# PyInstaller spec — builds a single, size-trimmed FastBreak.exe
# Usage: pyinstaller --noconfirm --clean FastBreak.spec
import os
import re
import sys
from pathlib import Path

ROOT = Path(SPECPATH)
_src = (ROOT / "fastbreak" / "__init__.py").read_text(encoding="utf-8")
VERSION = os.environ.get("FASTBREAK_VERSION", "").lstrip("v") or \
    re.search(r'__version__ = "([^"]+)"', _src).group(1)
_nums = [int(n) for n in re.findall(r"\d+", VERSION)[:4]]
VTUPLE = tuple(_nums + [0] * (4 - len(_nums)))

# --- Windows version resource ---------------------------------------------
_vfile = None
if sys.platform == "win32":
    from PyInstaller.utils.win32.versioninfo import (FixedFileInfo, StringFileInfo, StringStruct,
                                                     StringTable, VarFileInfo, VarStruct,
                                                     VSVersionInfo)

    _vinfo = VSVersionInfo(
        ffi=FixedFileInfo(filevers=VTUPLE, prodvers=VTUPLE),
        kids=[
            StringFileInfo([StringTable("040904B0", [
                StringStruct("FileDescription", "FastBreak"),
                StringStruct("FileVersion", VERSION),
                StringStruct("ProductName", "FastBreak"),
                StringStruct("ProductVersion", VERSION),
                StringStruct("OriginalFilename", "FastBreak.exe"),
                StringStruct("LegalCopyright", "MIT License"),
            ])]),
            VarFileInfo([VarStruct("Translation", [0x0409, 1200])]),
        ],
    )
    _vfile = Path(workpath) / "version_info.txt"
    _vfile.parent.mkdir(parents=True, exist_ok=True)
    _vfile.write_text(str(_vinfo), encoding="utf-8")

# --- Analysis --------------------------------------------------------------
EXCLUDES = [
    "tkinter", "_tkinter", "unittest", "pydoc", "doctest", "pdb", "lib2to3", "xmlrpc",
    "sqlite3", "_sqlite3", "ssl", "_ssl", "bz2", "_bz2", "lzma", "_lzma", "asyncio",
    "multiprocessing", "ftplib",
    "PySide6.QtNetwork", "PySide6.QtSvg", "PySide6.QtOpenGL", "PySide6.QtOpenGLWidgets",
    "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtPdf", "PySide6.QtDBus",
    "PySide6.QtPrintSupport", "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtXml",
    "PySide6.QtConcurrent",
]

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    datas=[(str(ROOT / "assets" / f), "assets")
           for f in ("logo.png", "icon-16.png", "icon-32.png", "icon-256.png")],
    excludes=EXCLUDES,
    noarchive=False,
)

# Keep only what a QtWidgets app needs: the Windows platform plugin.
_DROP_PREFIX = ("opengl32sw", "d3dcompiler", "Qt6Network", "Qt6Svg", "Qt6Pdf", "Qt6Qml",
                "Qt6Quick", "Qt6OpenGL", "Qt6VirtualKeyboard", "Qt6DBus", "Qt6PrintSupport",
                "Qt6Sql", "Qt6Test", "Qt6Xml", "Qt6Concurrent", "libssl", "libcrypto")


def _keep(entry):
    dest = entry[0].replace("\\", "/")
    name = dest.rsplit("/", 1)[-1]
    if "/plugins/" in dest:
        return name == "qwindows.dll"
    if "/translations/" in dest:
        return False
    return not name.startswith(_DROP_PREFIX)


a.binaries = [b for b in a.binaries if _keep(b)]
a.datas = [d for d in a.datas if _keep(d)]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="FastBreak",
    console=False,
    debug=False,
    strip=False,
    upx=False,  # UPX breaks Qt plugins and triggers antivirus false positives
    icon=str(ROOT / "assets" / "icon.ico"),
    version=str(_vfile) if _vfile else None,
)
