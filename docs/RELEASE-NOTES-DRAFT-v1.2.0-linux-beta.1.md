# DRAFT release notes — v1.2.0-linux-beta.1 (Linux beta)

> **STATUS: DRAFT — NOT PUBLISHED.** Prepared by REL-0 for the Owner's
> release decision. Do not attach to any GitHub Release until the Owner
> approves publication (see `docs/REL0-LINUX-BETA-FINALIZATION.md`,
> "Public Release Gate").
>
> Owner actions at publication time:
> 1. Create tag `v1.2.0-linux-beta.1` at the exact commit recorded in the
>    REL-0 report ("Final RC Source Commit") — the commit the release CI
>    run built.
> 2. Create the GitHub Release with **prerelease: true**, title
>    `RhythmAlign v1.2.0-linux-beta.1 (Linux beta)`.
> 3. Attach `RhythmAlign-v1.2.0-linux-x86_64-beta.tar.gz`, its `.sha256`
>    sidecar, and `build-env-frozen.txt` from that CI run.
> 4. Fill the two placeholders below from the REL-0 report.
> 5. Do NOT touch the stable Windows `v1.2.0` release, `update.json`, or
>    any existing asset.

---

## RhythmAlign v1.2.0-linux-beta.1 — Linux beta (x86_64)

This is the first **Linux beta** of RhythmAlign, the auto audio-video
sync tool for rhythm game hand-cams. It is built from the same Engine v2
core as the Windows v1.2.0 release and produces bit-identical alignment
decisions.

**This is a beta:** it is feature-complete for the alignment workflow but
receives less testing than the Windows release. Please report issues at
https://github.com/Daozhu1007/RhythmAlign/issues.

- **Platform:** Linux x86_64 only (no ARM builds in this beta)
- **Requirement:** glibc **>= 2.35** — e.g. Ubuntu 22.04+, Debian 12+,
  Fedora 36+, Linux Mint 21+, Arch, openSUSE Tumbleweed
- **Format:** portable `.tar.gz` — no installer, no Python needed;
  extract and run
- **GPU acceleration:** unavailable in this beta (software encoding
  via the bundled FFmpeg/libx264); export quality is unaffected
- **Updates:** manual — this beta does not self-update; check the
  Releases page
- **Windows users:** stay on the stable Windows v1.2.0 — this release
  does not appear in the in-app updater for Windows installs

### Install

```bash
tar xzf RhythmAlign-v1.2.0-linux-x86_64-beta.tar.gz
cd RhythmAlign
./RhythmAlign
```

Optional desktop menu entry (user-local, removable):

```bash
./install-desktop-integration.sh           # add menu entry
./install-desktop-integration.sh --remove  # remove it again
```

Notes:
- On Wayland or a full desktop environment it just works; on minimal X11
  sessions install `libxkbcommon-x11-0` and `libxcb-cursor0` if the
  window fails to appear.
- On minimal systems without CJK fonts, install one (e.g.
  `fonts-noto-cjk`) for Chinese UI text.

### Downloads

| File | SHA256 |
|---|---|
| `RhythmAlign-v1.2.0-linux-x86_64-beta.tar.gz` | `[TO FILL FROM .sha256 SIDECAR AT PUBLICATION]` |

- **Exact source commit (RC):** `[TO FILL FROM REL-0 REPORT — the commit the release CI run built]`
- `build-env-frozen.txt` records the exact dependency versions of the
  build environment.

### License

RhythmAlign is released under the PolyForm Noncommercial 1.0.0 (see
`LICENSE`). Third-party components are governed by their own licenses —
see `THIRD-PARTY-NOTICES.txt` in the archive.
