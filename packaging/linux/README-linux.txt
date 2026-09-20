RhythmAlign Linux beta (x86_64)
================================

Auto audio-video sync for rhythm game hand-cams.
https://github.com/Daozhu1007/RhythmAlign

Launch
------
    tar xzf RhythmAlign-v*.tar.gz
    cd RhythmAlign
    ./RhythmAlign

No Python, pip, or installation is required.

System requirements
-------------------
- Linux x86_64 with glibc >= 2.35. This covers Ubuntu 22.04+, Debian 12+,
  Fedora 36+, Linux Mint 21+, and other distributions on equivalent libc.
- A display: native Wayland, or X11 with the standard xcb libraries that
  desktop distributions ship by default. On unusually minimal X11 systems
  install: libxkbcommon-x11-0 libxcb-cursor0 (Debian/Ubuntu names).
- For Chinese UI text on minimal systems install a CJK font, e.g.
  fonts-noto-cjk (standard desktop distributions already include one).

Desktop menu entry (optional, user-local)
-----------------------------------------
    ./install-desktop-integration.sh          # add
    ./install-desktop-integration.sh --remove # remove

This writes only into your user profile (~/.local/share/applications).

Export notes
------------
- The default "Video Stream Copy" export remuxes without re-encoding.
- This beta bundles an FFmpeg build with software encoding (libx264) only;
  the "Use GPU" toggle is therefore disabled on Linux. Export quality and
  behavior are unaffected.

Updates
-------
This beta does not self-update. When a new version is announced, the
in-app check opens the GitHub Releases page for you to download the
newest archive.

Troubleshooting
---------------
- If the window does not appear, run ./RhythmAlign from a terminal and
  read the error. To force a display backend:
      QT_QPA_PLATFORM=xcb      ./RhythmAlign    # X11
      QT_QPA_PLATFORM=wayland  ./RhythmAlign    # Wayland

License
-------
PolyForm Noncommercial 1.0.0 — see LICENSE in this directory.
