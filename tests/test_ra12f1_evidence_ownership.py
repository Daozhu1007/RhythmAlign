"""Peak ownership regressions, through the production curve/decision seam.

No media-specific offsets or policy floors are embedded in production.
The same-method stress case widens only its test clustering tolerance so
two peaks separated by the generator's 1.5 s refractory distance fit in
the former scoring window. Production defaults remain unchanged.
"""
import itertools

import numpy as np
import pytest

import alignment_engine_v2 as eng

SR, HOP, NV = 22050, 512, 3000
FRAME = HOP / SR


def family(method, peaks):
    curve = np.tile([-1.0, 1.0], 3000)
    for offset, height in peaks:
        curve[eng._offset_to_index(offset, NV, HOP, SR)] = height
    return eng.FamilyResult(method, eng.METHOD_FAMILY[method], curve, NV,
                            eng._correlation_z_score(curve), 0.0)


def decide(families, policy=None):
    return eng.decide_from_families(families, SR, HOP, policy, 120.0, 90.0)


def cluster_at(decision, offset):
    return min(decision.clusters,
               key=lambda c: abs(c["representative_offset_s"] - offset))


def assert_owned_suppliers(decision):
    owners = {}
    for cl in decision.clusters:
        candidates = {c["peak_id"]: c for c in cl["candidates"]}
        for peak in candidates:
            assert peak not in owners
            owners[peak] = cl
        for fam, winner in cl["families"].items():
            supplier = candidates[winner["supplier_peak_id"]]
            assert winner["supplier_owned"] is True
            assert supplier["family"] == fam
            assert supplier["method"] == winner["supplier_method"]
            assert supplier["peak_index"] == winner["supplier_peak_index"]
            assert supplier["offset_s"] == winner["supplier_peak_offset_s"]


def structural_pair():
    # Separation is outside membership but inside the old +/-13-frame
    # scoring radius, matching F0's topology without using personal media.
    h1, h2 = 10.0, 10.0 + 11 * FRAME
    return h1, h2, [
        family("hybrid", [(h1 - 2 * FRAME, 10), (30, 6)]),
        family("pcen_hpss", [(h1, 25), (30, 8)]),
        family("onset", [(h2, 3), (20, 4)]),
        family("pcen", [(h2, 5.2), (20, 5.4)]),
    ]


def test_structural_regression_and_one_peak_one_hypothesis():
    h1, h2, families = structural_pair()
    d = decide(families)
    assert d.accepted and d.reason_code == eng.ACCEPT_DUAL_FAMILY
    assert d.offset == pytest.approx(h1, abs=FRAME)
    true, false = cluster_at(d, h1), cluster_at(d, h2)
    assert true is not false
    assert true["case_a_failed_checks"] == []
    primary = false["families"][eng.FAMILY_PCEN]
    assert primary["supplier_method"] == "pcen"
    assert primary["z_at_cluster"] < eng.DEFAULT_POLICY.pcen_primary_z_floor
    assert primary["margin_at_cluster"] < eng.DEFAULT_POLICY.margin_floor_b
    assert {"pcen_z", "pcen_margin"} <= set(false["case_b_failed_checks"])
    assert_owned_suppliers(d)
    supplier_ids = [cl["families"][eng.FAMILY_PCEN]["supplier_peak_id"]
                    for cl in d.clusters if eng.FAMILY_PCEN in cl["families"]]
    assert len(supplier_ids) == len(set(supplier_ids))


def test_same_method_weak_owned_peak_cannot_borrow_strong_neighbor():
    policy = eng.DecisionPolicy(cluster_tol_s=0.8)
    h1, h2 = 10.0, 10.0 + 66 * FRAME
    assert 1.5 < h2 - h1 < 2 * policy.cluster_tol_s
    pcen = family("pcen_hpss", [(h1, 25), (h2, 5.2), (30, 4)])
    d = decide([family("hybrid", [(h1, 10)]), pcen,
                family("onset", [(h2, 3)])], policy)
    true, false = cluster_at(d, h1), cluster_at(d, h2)
    own = false["families"][eng.FAMILY_PCEN]
    assert own["supplier_method"] == "pcen_hpss"
    assert own["supplier_peak_offset_s"] == pytest.approx(h2, abs=FRAME)
    assert own["supplier_peak_id"] != true["families"][eng.FAMILY_PCEN]["supplier_peak_id"]
    assert own["z_at_cluster"] < policy.pcen_primary_z_floor
    # The unowned strong peak remains a competitor, even inside the former
    # window. It cannot supply either the numerator or an inflated margin.
    assert own["margin_at_cluster"] == pytest.approx(5.2 / 25, abs=0.001)
    assert "pcen_z" in false["case_b_failed_checks"]
    assert d.accepted and d.reason_code == eng.ACCEPT_DUAL_FAMILY
    assert_owned_suppliers(d)


def test_genuinely_supported_alternatives_remain_ambiguous():
    h1, h2 = 10.0, 20.0
    # Equal primary peaks: both hypotheses have their own CASE A evidence.
    d = decide([family("hybrid", [(h1, 12), (h2, 12)]),
                family("pcen_hpss", [(h1, 18), (h2, 18)])])
    assert d.reason_code == eng.ABSTAIN_AMBIGUOUS_CLUSTER
    assert not d.accepted and d.offset is None
    assert cluster_at(d, h1)["case_a_failed_checks"] == []
    assert cluster_at(d, h2)["case_a_failed_checks"] == []
    assert_owned_suppliers(d)


def test_pcen_siblings_aggregate_once_and_identify_winner():
    d = decide([family("pcen", [(10, 12)]),
                family("pcen_hpss", [(10, 25)])])
    cl = cluster_at(d, 10)
    assert set(cl["families"]) == {eng.FAMILY_PCEN}
    assert cl["families"][eng.FAMILY_PCEN]["methods"] == ["pcen", "pcen_hpss"]
    assert cl["families"][eng.FAMILY_PCEN]["supplier_method"] == "pcen_hpss"
    assert not d.accepted
    assert d.reason_code == eng.ABSTAIN_PRIMARY_NOT_CORROBORATED


@pytest.mark.parametrize("height,onset,expected", [
    (25, False, False), (5.2, True, False), (25, True, True),
])
def test_case_b_safeguards(height, onset, expected):
    families = [family("pcen_hpss", [(10, height), (30, 4)])]
    if onset:
        families.append(family("onset", [(10, 3)]))
    d = decide(families)
    assert d.accepted is expected
    if expected:
        assert d.reason_code == eng.ACCEPT_PRIMARY_WITH_CORROBORATION


def test_generator_order_does_not_change_ownership_or_decision():
    _, _, families = structural_pair()
    expected = decide(families)
    for order in itertools.permutations(families):
        d = decide(order)
        assert (d.status, d.reason_code, d.offset, d.clusters) == (
            expected.status, expected.reason_code, expected.offset, expected.clusters)


def test_moving_representative_retains_earlier_owned_peak():
    # The upper median moves twice; scoring still uses the earliest owned
    # nomination at its exact curve index, never at the new representative.
    h = 10.0
    families = [family("hybrid", [(h, 10)]),
                family("pcen_hpss", [(h + 6 * FRAME, 25)]),
                family("pcen", [(h + 12 * FRAME, 12)]),
                family("onset", [(h + 12 * FRAME, 3)])]
    expected = decide(families)
    cl = cluster_at(expected, h + 12 * FRAME)
    assert len(cl["candidates"]) == 4
    assert cl["representative_offset_s"] == pytest.approx(h + 12 * FRAME, abs=FRAME)
    assert cl["families"][eng.FAMILY_TONAL]["supplier_peak_offset_s"] == pytest.approx(h, abs=FRAME)
    assert expected.accepted
    for order in itertools.permutations(families):
        d = decide(order)
        assert d.clusters == expected.clusters
        assert d.offset == expected.offset
    assert_owned_suppliers(expected)


@pytest.mark.parametrize("gap_frames,same_cluster", [(6, True), (7, False)])
def test_membership_tolerance_boundary(gap_frames, same_cluster):
    d = decide([family("hybrid", [(10, 10)]),
                family("pcen_hpss", [(10 + gap_frames * FRAME, 25)])])
    cl = cluster_at(d, 10)
    assert (eng.FAMILY_PCEN in cl["families"]) is same_cluster
    assert d.accepted is same_cluster
    assert_owned_suppliers(d)


@pytest.mark.parametrize("gap_frames", [12, 13, 14])
def test_former_scoring_window_boundary_cannot_import_unowned_peak(gap_frames):
    h1, h2 = 10.0, 10.0 + gap_frames * FRAME
    d = decide([family("hybrid", [(h1, 10)]),
                family("pcen_hpss", [(h1, 25)]),
                family("pcen", [(h2, 5.2), (30, 5.4)]),
                family("onset", [(h2, 3)])])
    false = cluster_at(d, h2)
    assert false["families"][eng.FAMILY_PCEN]["supplier_method"] == "pcen"
    assert "pcen_z" in false["case_b_failed_checks"]
    assert d.accepted
    assert_owned_suppliers(d)


def test_exact_membership_boundary_is_inclusive():
    gap = 6 * FRAME
    actual = abs(eng._index_to_offset(eng._offset_to_index(10 + gap, NV, HOP, SR), NV, HOP, SR)
                 - eng._index_to_offset(eng._offset_to_index(10, NV, HOP, SR), NV, HOP, SR))
    families = [family("hybrid", [(10, 10)]), family("pcen_hpss", [(10 + gap, 25)])]
    assert decide(families, eng.DecisionPolicy(cluster_tol_s=actual)).accepted
    assert not decide(families, eng.DecisionPolicy(cluster_tol_s=np.nextafter(actual, 0))).accepted


def test_temporal_gate_uses_family_supplier_from_owning_cluster():
    h1, h2, families = structural_pair()
    d = decide(families)
    # Nearby unrelated candidate must not hijack verification; the winner
    # field is authoritative even when another sibling candidate has high Z.
    false = cluster_at(d, h2)
    next(c for c in false["candidates"] if c["family"] == eng.FAMILY_PCEN)["z"] = 1000
    assert eng._deciding_pcen_method(d.clusters, d.offset) == "pcen_hpss"
    siblings = decide([family("hybrid", [(10, 10)]),
                       family("pcen_hpss", [(10, 12)]),
                       family("pcen", [(10, 25)])])
    assert siblings.accepted
    assert eng._deciding_pcen_method(siblings.clusters, siblings.offset) == "pcen"
    assert_owned_suppliers(siblings)
