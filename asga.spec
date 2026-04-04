# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


repo_root = Path.cwd()
data_files = [
    (str(repo_root / "cooperation_ga" / "data" / "ann_weights.csv"), "cooperation_ga/data"),
    (str(repo_root / "sample_config.json"), "."),
    (str(repo_root / "sample_render_config.json"), "."),
    (str(repo_root / "config_1000_steps_all_strategies_20_fast.json"), "."),
    (str(repo_root / "config_1000_steps_all_strategies_20_render_static.json"), "."),
    (str(repo_root / "config_10000_steps_all_strategies_20_fast.json"), "."),
    (str(repo_root / "config_10000_steps_all_strategies_20_render_static.json"), "."),
]


a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=data_files,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="asga",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
