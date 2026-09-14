# Final Source Pool Gap

Status: `FINAL_SOURCE_POOL_INSUFFICIENT` → **RESOLVED 2026-09-15**
(see `FINAL_SOURCE_SELECTION.md`)

> **2026-09-15 resolution note (historical record preserved below, never
> deleted).** The insufficient pool documented on this page has been
> resolved by the owner's fresh folder
> `D:\Daozh\Music\RhythmAlign_FinalCandidates_Fresh` (13 files → 11 clean
> eligible identities). The final source freeze, the 26-take acquisition
> manifest, and the playback kit now exist; see
> `FINAL_SOURCE_SELECTION.md` and
> `experiments/applied_system/final_pack/`. The alias audit performed
> during that resolution additionally found that THREE of the four
> "remaining final-eligible identities" tabled below were wrong at the
> identity level and are now PERMANENTLY_EXCLUDED_HISTORICAL, with
> evidence recorded in the freeze: **Scarlet Lance = 红枪** (result-screen
> evidence), **さよならプリンセス = 再见公主** (result-screen evidence),
> and **Sage** (production RhythmAlign outputs `Sage_synced*.mp4`). Only
> **ARROW** survives from the table below, and it is S06 of the final
> freeze. The protocol, the ledger snapshot
> `ab7572e352421e433b3ed6aff009fdc437d3c57bca73e257c626fcaef5385b9e`, and
> the "6 + 1 missing sources" numbers below are historical statements of
> that date; the missing-count requirement was satisfied by the fresh
> intake. NO COMPARATOR WAS RUN AT ANY POINT, in either audit.

This document records the performance-blind source audit required before the
final acquisition kit can be built. The frozen benchmark protocol was not
changed. No final source ledger, playback buffer, acquisition manifest, or
owner recording guide was created because the minimum source pool is not
available.

## Audit result

The two authorized read-only roots were rechecked:

- `D:\Daozh\Videos`
- `D:\Daozh\Music`

The live scan found 40 audio files and 38 unique SHA-256 identities. The
current inventory hashes matched the live files exactly: 0 changed paths and
0 missing paths. Two duplicate file rows were collapsed (`分诊` and `海底谭`).

## New candidate intake — 2026-09-14

The owner-supplied read-only folder
`D:\Daozh\Music\RhythmAlign_FinalCandidates` contained 12 audio files and 12
unique SHA-256 identities. Every file decoded successfully as an MP3 with two
channels. There were no exact-hash duplicates. Embedded ID3 title/artist data
was recorded when present; the filename and metadata were resolved against the
frozen historical ledger before any suitability decision. Historical exposure
takes precedence over technical suitability.

| File | ID3 title / artist | SHA-256 | Duration (s) | Codec | Hz | Ch | Classification | Historical identity / evidence |
|---|---|---|---:|---|---:|---:|---|---|
| `39.mp3` | `39` / `sasakure.UK x DECO*27` | `3361af45d8db5642bb8724fec1fd96bc07ffa769ecb7826bb7525e25212059f6` | 118.971 | MPEG_LAYER_III | 48000 | 2 | `PERMANENTLY_EXCLUDED_HISTORICAL` | 白39 / 39; RA-1.2 holdout |
| `90decision.mp3` | `The 90's Decision` / `MYUKKE.` | `e2249aa098808f529c9b2939cfff0cc4effc9ec3d7bebc7319b10dfc6d5416e4` | 135.938 | MPEG_LAYER_III | 48000 | 2 | `PERMANENTLY_EXCLUDED_HISTORICAL` | 90decision; RA-1.2 calibration |
| `DROPS.mp3` | `DROPS feat. Such` / `Zekk & poplavor` | `2b8be94ae159ee47ac29c7bb62f931603d712aabec4ff7571469033e36099879` | 157.994 | MPEG_LAYER_III | 48000 | 2 | `PERMANENTLY_EXCLUDED_HISTORICAL` | DROPS; RA-1.2 calibration |
| `乐意效劳.mp3` | `はいよろこんで` / `こっちのけんと` | `53092e34259a9ccce9f8aaff3a89946910c0546e2b38a8a36294dee66852c25c` | 162.037 | MPEG_LAYER_III | 48000 | 2 | `PERMANENTLY_EXCLUDED_HISTORICAL` | 乐意效劳; RA-1.2 holdout |
| `分诊.mp3` | `music001298 (Play)` / unavailable | `3b657251300246ae34f742efe9221eb4a279fe7f61714bf9a54580af2c916b75` | 145.000 | MPEG_LAYER_III | 44100 | 2 | `PERMANENTLY_EXCLUDED_HISTORICAL` | 分诊; RA-1.2 calibration |
| `妄想感伤代偿联盟.mp3` | `妄想感傷代償連盟` / `DECO*27` | `979d08ecae6607dc937b5eedc94a80f37937ce77a20d22fff289c6ff750a0a0c` | 145.990 | MPEG_LAYER_III | 48000 | 2 | `PERMANENTLY_EXCLUDED_HISTORICAL` | 白妄想 / 妄想感伤代偿联盟; RA-1.2 calibration |
| `宙天.mp3` | `宙天` / `t+pazolite vs かねこちはる` | `78a3ac4a2a9cb9a1af3125880584225d935ba1207733f66c2b1ead2938ed94a9` | 161.165 | MPEG_LAYER_III | 48000 | 2 | `PERMANENTLY_EXCLUDED_HISTORICAL` | 宙天; RA-1.2 holdout |
| `巴别塔.mp3` | `バベル` / `いよわ feat.重音テト` | `0a4776360a6a8e8fac3456451e62cea2bd252544b20fc408db4b956b7fe7ef1f` | 149.333 | MPEG_LAYER_III | 48000 | 2 | `PERMANENTLY_EXCLUDED_HISTORICAL` | 巴别塔; RA-1.2 holdout |
| `延误列车.mp3` | `ラグトレイン` / `稲葉曇` | `2e1d85c61d7865596ef6e911f42d193fec344770ff7523836ef3aef51a293929` | 148.571 | MPEG_LAYER_III | 48000 | 2 | `PERMANENTLY_EXCLUDED_HISTORICAL` | 延误列车; calibration/Astra blocker |
| `心跳不止.mp3` | `music001512 (Play)` / unavailable | `038299da0ec6cb3d43daa164856e33e279a213c130efbc8b8d5a9cca20b68349` | 146.182 | MPEG_LAYER_III | 44100 | 2 | `PERMANENTLY_EXCLUDED_HISTORICAL` | 心跳不止; RA-1.2 dev corpus |
| `才不是恶魔呢.mp3` | `デビルじゃないもん` / `DECO*27, ピノキオピー` | `b577db861e35e50317df110bc90fb72c263d0c0fca3c886610f5f62a7d49658e` | 139.481 | MPEG_LAYER_III | 48000 | 2 | `PERMANENTLY_EXCLUDED_HISTORICAL` | 才不是恶魔呢; RA-1.2 holdout |
| `海底谭.mp3` | `music000417 (Play)` / unavailable | `d5b999943988a2ebcd4172699d981c5d50241b6453a43ffe9dfbb888aa7c9f06` | 137.321 | MPEG_LAYER_III | 44100 | 2 | `PERMANENTLY_EXCLUDED_HISTORICAL` | 海底谭 / ウミユリ海底譚; holdout/dev corpus |

The 12 new files therefore add **0** `FINAL_ELIGIBLE` identities, **0**
duplicates, and **0** technically unsuitable identities. They are all
`PERMANENTLY_EXCLUDED_HISTORICAL`; none is a new pilot identity. No source
comparator, fingerprint system, or alignment system was run on this folder.

Classification of the 38 unique identities:

| Class | Count | Result |
|---|---:|---|
| `PERMANENTLY_EXCLUDED_HISTORICAL` | 31 | Prior development, calibration, holdout, Astra, or shakedown exposure; aliases and version variants included |
| `PERMANENTLY_EXCLUDED_PILOT` | 3 | Bloody Trail; スティールユー / Steel You; Divide et impera |
| `DUPLICATE` | 0 unique identities | Two duplicate file copies were collapsed before identity counting |
| `TECHNICALLY_UNSUITABLE` | 0 | The seven nonhistorical clean-pool files decoded successfully; historical exclusion takes precedence for the other identities |
| `FINAL_ELIGIBLE` | 4 | Listed below |

The historical class preserves the prior 27 named exclusion rows, including
the grouped alias/version rows for `分诊`, `海底谭`, `Override`, and the three
Arcaea files. Their 33 file rows reduce to 31 unique SHA-256 identities after
the two exact duplicate copies are collapsed. The historical ledger was
checked against the current research documents, the pilot manifests, and the
archive tags.

## Remaining final-eligible identities

All four remaining identities were re-probed as native 48 kHz, stereo MP3
files and decoded successfully. They have not been used as comparator inputs
and were not selected for the pilot.

| Identity | Local source | SHA-256 | Duration (s) |
|---|---|---|---:|
| ARROW | `D:\Daozh\Music\舞萌手元用\ARROW.mp3` | `3e61a90722f1a979a92f294c7256566bc796130deeabb35524f265caa4fe0ee6` | 232.083 |
| Scarlet Lance | `D:\Daozh\Music\舞萌手元用\Scarlet Lance - MASAKI (ZUNATA) - Groove Coaster Originals BGs.mp3` | `b57f61bbdd2fef77d6635fbdd126def25f5cd9494a7b8ad18c07cca0ac502585` | 128.331 |
| Sage | `D:\Daozh\Music\舞萌手元用\かめりあ(Camellia) - Sage [From maimai でらっくす] - Camellia Official.mp3` | `829bc0c618c5a18c5bde0f9c0cf380f0139f00707c378e4ce4778d8006f583d3` | 151.492 |
| さよならプリンセス / Sayonara Princess | `D:\Daozh\Music\舞萌手元用\さよならプリンセス _ 初音ミク - Kai.mp3` | `c7a499482e4e256ec46160d66a6e8eac679ba53dec39620fa66bea1d32506bcb` | 126.051 |

These four identities remain eligible and were reverified against their prior
hashes. They are not enough to fill S01–S10, and reserving them leaves no
separate eligible interference identity.

For provenance, the deterministic source-only long-lag chroma recurrence
scores (`R_long`) of the four survivors were recomputed without comparator
execution: ARROW `0.95204`, Scarlet Lance `0.97226`, Sage `0.94717`, and
さよならプリンセス `0.97437`. These are structural descriptors only; no
repetitive-stress classification was frozen because no final slots were
selected.

## Missing sources

The frozen protocol requires 10 unique final reference identities and at least
one separate eligible interference identity. The current pool provides four
reference-eligible identities and no separate eligible interference identity
after those four are reserved.

- Final reference sources still needed: **6**
- Separate interference source still needed: **1**
- Minimum fresh song identities to provide: **7**
- Final-data acquisition may begin: **NO**

For the next intake, please provide at least seven complete, locally
accessible songs that have never appeared in RhythmAlign development,
shakedown, pilot, Astra, holdout, or comparator work. The safe screening
target is a stable exact file/version of at least 150 seconds, cleanly
decodable audio (WAV, FLAC, MP3, M4A, AAC, OGG, OPUS, or WMA), and no severe
leading or trailing silence. These are intake-screening requirements for the
next selection pass, not amendments to the frozen benchmark protocol.

The owner does not need to choose songs scientifically. Put the fresh files in
a separate folder or provide their paths; the next selection pass will hash,
screen, check identity history, and apply the deterministic source-only rule.
Providing more than seven reduces the risk that duration, identity, or
structural screening leaves fewer than six reference choices.

The new intake does not alter the frozen exclusion ledger or protocol. The
ledger snapshot remains `ab7572e352421e433b3ed6aff009fdc437d3c57bca73e257c626fcaef5385b9e`;
the 12-file intake audit above is an extension of its application, not a
replacement or result-dependent edit.

## Contamination boundary

No RhythmAlign, GCC-PHAT, Panako, NCC, or Kdenlive execution was performed on
any final candidate, and no final buffer or recording was generated. The
existing pilot material remains permanently excluded:

- Bloody Trail
- スティールユー / Steel You
- Divide et impera

No copyrighted audio was added to Git, no production code was changed, and the
authorized source roots were read-only throughout.

## Owner-facing request

还缺 6 首新的最终参考歌曲和 1 首单独的干扰歌曲；请把至少 7 首从未参加过 RhythmAlign 实验的完整歌曲放到一个文件夹里，不需要你做科学选择。
