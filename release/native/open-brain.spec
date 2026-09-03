from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = Path(SPECPATH).parents[1]
ENTRYPOINT = ROOT / "packages/app/src/open_brain/services/native_entrypoint.py"

hiddenimports = sorted(
    set(
        collect_submodules("open_brain")
        + collect_submodules("open_brain_engine")
    )
)
datas = sorted(
    collect_data_files("open_brain") + collect_data_files("open_brain_engine"),
    key=lambda item: (item[1], item[0]),
)

analysis = Analysis(
    [str(ENTRYPOINT)],
    pathex=[
        str(ROOT / "packages/app/src"),
        str(ROOT / "packages/engine/src"),
    ],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["open_brain_connectors", "open_brain_legacy"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(analysis.pure)
executable = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="open-brain",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
artifact = COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="open-brain",
)
