# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import copy_metadata

datas = [
    ('assets', 'assets'),
    ('locales', 'locales'),
    ('config.json', '.'),
]
datas += copy_metadata('imageio_ffmpeg')


def _drop_dev_only_data(toc):
    dev_only_markers = (
        'sklearn/datasets/tests/',
    )
    filtered = []
    for entry in toc:
        normalized = '/'.join(str(value).replace('\\', '/') for value in entry[:2]).lower()
        if any(marker in normalized for marker in dev_only_markers):
            continue
        filtered.append(entry)
    return filtered


a = Analysis(
    ['ui_main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', '_pytest'],
    noarchive=False,
    optimize=0,
)
a.datas = _drop_dev_only_data(a.datas)
a.binaries = _drop_dev_only_data(a.binaries)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='RhythmAlign',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/logo.ico',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='RhythmAlign',
)
