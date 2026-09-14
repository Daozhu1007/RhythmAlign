# Final Source Pool Gap

Status: `FINAL_SOURCE_POOL_INSUFFICIENT`

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

These four identities cannot be frozen as S01–S10: doing so would require
reusing exposed pilot material or fabricating/reusing identities.

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
