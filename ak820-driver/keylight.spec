# -*- mode: python ; coding: utf-8 -*-
"""How Keylight is packed into one portable folder.

    pyinstaller --clean --noconfirm keylight.spec

The result is ``dist/Keylight/`` - ``Keylight.exe`` beside an
``_internal`` folder. Nothing is extracted to the temp folder at start,
and every file the app writes (profiles, macros, settings, the log) goes
into the same folder as the exe, so the folder can be copied to a USB
stick and taken anywhere.

The front end is not a Python file, so it goes in as data and the server
finds it in the folder the packer puts it in. The window toolkit
(``pywebview``) reaches the Edge WebView2 runtime through a back end
that PyInstaller cannot see on its own, so it is named here.
"""

from pathlib import Path

ROOT = Path(SPECPATH).resolve()

# The files that are data rather than code: the front end, and the
# board's own definition.
datas = [
    (str(ROOT / "ui"), "ui"),
    (str(ROOT / "ak820" / "devices"), "ak820/devices"),
]

# The window toolkit picks its back end at run time.
hiddenimports = [
    "webview",
    "webview.platforms.edgechromium",
    "webview.platforms.mshtml",
    "clr_loader",
    "pythonnet",
]

a = Analysis(
    [str(ROOT / "ak820" / "app.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "pytest", "IPython"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Keylight",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    # No console window: the app is a window, not a terminal. Anything
    # worth saying goes to keylight.log beside the app.
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
    upx=True,
    upx_exclude=[],
    name="Keylight",
)
