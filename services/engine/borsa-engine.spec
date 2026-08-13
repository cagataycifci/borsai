# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Borsa engine sidecar (Phase 10).

Build (from services/engine, venv active):
    pyinstaller borsa-engine.spec --noconfirm

Output: dist/borsa-engine/ (one-folder bundle) — electron-builder copies this
into extraResources as resources/engine/.
"""

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

hiddenimports = (
    collect_submodules("app")
    + collect_submodules("uvicorn")
    + collect_submodules("google.genai")
    + ["google.genai"]
)

a = Analysis(
    ["app/main.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("app/data/universe/bist_seed.json", "app/data/universe"),
        ("alembic", "alembic"),
        ("alembic.ini", "."),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="borsa-engine",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="borsa-engine",
)
