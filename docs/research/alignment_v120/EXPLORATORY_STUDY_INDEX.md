# EXPLORATORY STUDY INDEX — pre-v1.2.0 Astra alignment study (archived)

The old study is preserved historically on its own branch and is **not**
rewritten, merged, or copied into this branch. This index only points to it.

- Branch: `astra/alignment-research-wip` (local-only; unmerged; not pushed)
- WIP preservation commit: `5b1fcd472a94470872dc1f837a7f473c0edd5282`
  (created during the RA-1.2D pre-flight, owner-approved, to keep `main` clean;
  see `docs/RA-1.2D-DEFAULT-INTEGRATION.md` §1)
- Completed research commit: `8b78eb1f18ecf1ec2e9e1afa374dc2ac93a7b40e`
- Scientific baseline of the study: `ffa6b07a591dbdb54ae8350f3d27dce3ed74c847`
  (RA-1.2C state — Engine v2 implemented but NON-default; the study also
  verified engine-code AST equality at `20d4816`, i.e. RA-1.2D)

Key reports on that branch:

- `docs/research/alignment/ALIGNMENT_RESEARCH_STUDY.md` — full study;
  verdicts `ENGINEERING_ONLY` + `RELEASE_BLOCKER_FOUND` (pre-v1.2.0 system)
- `docs/research/alignment/EXPERIMENT_PLAN.md` — protocol + completion record
- `docs/research/alignment/LITERATURE_REVIEW.md` — citations + novelty boundary
- `experiments/alignment_research/` — scripts, committed result JSONs, figures

Load-bearing statements:

1. The study evaluated a **pre-v1.2.0 system** (Engine v2 without the
   temporal-support safeguard, non-default at the scientific baseline).
2. Its principal discovery — concentrated-evidence wrong-song acceptance,
   minimum regression `tr_lingduihua` → `tr_yanwulieche` at +1.462857 s with
   94.563 % plain-PCEN concentration in one ~1 s bin — directly motivated
   **RA-1.2D1** (`docs/RA-1.2D1-TEMPORAL-SUPPORT-SAFEGUARD.md`), which is part
   of the released v1.2.0.
3. **Its benchmark results and verdicts must never be reported as v1.2.0
   results.** All measurements describe the pre-D1 engine state.
4. The 18 component-A clean-grid wrong accepts are the DEV data that selected
   the released `max_top_bin_share = 0.25`; they can never confirm the
   safeguard's generalization (see `DATA_PROVENANCE.md`).
