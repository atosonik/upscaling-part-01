# PyInstaller spec for Lumina (onedir, no console).
# Weights stay beside the folder, not inside the bundle:
#   dist/Lumina/Lumina.exe
#   weights/   or   parts/   one level up (project root) or next to the exe
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = [], [], []
for package in (
    "torch",
    "torchvision",
    "spandrel",
    "einops",
    "safetensors",
    "cv2",
    "PyQt5",
):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(package)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

hiddenimports += ["chunker", "app", "app.config", "app.core", "app.ui"]
datas += [("chunker.py", ".")]

EXCLUDES = [
    "tkinter",
    "matplotlib",
    "IPython",
    "pytest",
    "unittest",
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=["app/rthook_qt.py"],
    excludes=EXCLUDES,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Lumina",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Lumina",
)
