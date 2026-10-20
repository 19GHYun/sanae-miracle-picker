# -*- coding: utf-8 -*-
"""
exe 빌드: dist\\SanaeMiracle.exe

  python build.py
  python build.py --print-version

아이콘(app.ico)은 사나에 얼굴로 빌드 때마다 새로 만든다.
이 앱은 QtWidgets 만 쓰므로 PySide6 가 딸려 보내는 것 중 안 쓰는 것(Qt Quick · QML · PDF · 네트워크 · OpenSSL ·
소프트웨어 OpenGL · 그림 형식 플러그인 …)은 빼서 exe 를 줄인다 (작을수록 처음 실행할 때 백신 검사도 빨리 끝남).
"""
from __future__ import annotations

import re
import struct
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENTRY = HERE / "sanae_picker.pyw"
BUILD_DIR = HERE / "build"
ICON = BUILD_DIR / "app.ico"
EXE_NAME = "SanaeMiracle"
PRODUCT = "사나에의 기적 추첨기"
COPYRIGHT = "Copyright (c) 2026 YGH. MIT License."
ICO_SIZES = [256, 128, 64, 48, 32, 24, 16]
_qt_app = None
# exe 에 넣지 않는 파일 (경로에 이 글자가 들어 있으면 뺌). PNG 는 Qt 에 들어 있어서 그림 형식 플러그인이 없어도 됨.
EXCLUDE_FILES = ("opengl32sw.dll", "qt6quick", "qt6qml", "qt6pdf", "qt6network", "qt6svg", "qt6virtualkeyboard",
                 "qt6opengl.dll", "libcrypto", "libssl",
                 "plugins/imageformats/", "plugins/iconengines/", "plugins/tls/", "plugins/networkinformation/",
                 "plugins/platforminputcontexts/", "plugins/generic/", "plugins/platforms/qdirect2d")
KEEP_TRANSLATIONS = ("qtbase_ko.qm", "qtbase_ja.qm")       # Qt 기본 글자 (예/아니요 단추 · 오른쪽 클릭 메뉴)
EXCLUDE_MODULES = ["PySide6.QtNetwork", "ssl", "_ssl", "_hashlib", "tkinter"]   # hashlib 은 내장 sha256 으로 충분

SPEC_TEMPLATE = """\
# build.py 가 만든 파일 — 고치려면 build.py 를 고치세요.
import pathlib

EXCLUDE = {exclude!r}
KEEP_QM = {keep_qm!r}


def keep(dest):
    d = pathlib.PureWindowsPath(dest).as_posix().lower()
    if "/translations/" in d:
        return d.endswith(KEEP_QM)
    return not any(x in d for x in EXCLUDE)


a = Analysis([{entry!r}], pathex=[{root!r}], datas=[({sprites!r}, "miracle/sprites")], excludes={modules!r})
a.binaries = [b for b in a.binaries if keep(b[0])]
a.datas = [x for x in a.datas if keep(x[0])]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name={name!r}, console=False, upx=False,
          icon=[{icon!r}], version={version_file!r})
"""

VERSION_TEMPLATE = """\
VSVersionInfo(
  ffi=FixedFileInfo(filevers={vt}, prodvers={vt}, mask=0x3f, flags=0x0,
                    OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'YGH'),
      StringStruct('FileDescription', {product!r}),
      StringStruct('FileVersion', {version!r}),
      StringStruct('InternalName', {exe!r}),
      StringStruct('LegalCopyright', {copyright!r}),
      StringStruct('OriginalFilename', {exe_file!r}),
      StringStruct('ProductName', {product!r}),
      StringStruct('ProductVersion', {version!r})])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""


def read_version() -> str:
    text = (HERE / "miracle" / "__init__.py").read_text(encoding="utf-8")
    m = re.search(r'^__version__\s*=\s*"(\d+\.\d+\.\d+)"', text, re.M)
    if not m:
        raise SystemExit('miracle/__init__.py 에서 __version__ = "x.y.z" 를 찾지 못했습니다.')
    return m.group(1)


def write_icon(path: Path) -> None:
    """앱 아이콘을 PNG 항목으로 된 다중 크기 .ico 로."""
    from PySide6.QtCore import QBuffer, QIODevice, QSize
    from PySide6.QtWidgets import QApplication
    sys.path.insert(0, str(HERE))
    from miracle.app import app_icon
    global _qt_app  # 아이콘을 그리는 동안 QApplication 이 살아 있어야 함
    _qt_app = QApplication.instance() or QApplication([])
    icon = app_icon()
    blobs = []
    for s in ICO_SIZES:
        buf = QBuffer()
        buf.open(QIODevice.WriteOnly)
        icon.pixmap(QSize(s, s)).toImage().save(buf, "PNG")
        blobs.append(bytes(buf.data()))
    offset = 6 + 16 * len(ICO_SIZES)
    head = struct.pack("<HHH", 0, 1, len(ICO_SIZES))
    for s, b in zip(ICO_SIZES, blobs):
        head += struct.pack("<BBBBHHII", s % 256, s % 256, 0, 0, 1, 32, len(b), offset)
        offset += len(b)
    path.write_bytes(head + b"".join(blobs))


def main() -> int:
    version = read_version()
    if len(sys.argv) > 1 and sys.argv[1] == "--print-version":
        print(version)
        return 0
    BUILD_DIR.mkdir(exist_ok=True)
    write_icon(ICON)
    version_file = BUILD_DIR / "version_info.txt"
    version_file.write_text(VERSION_TEMPLATE.format(
        vt=tuple(int(x) for x in version.split(".")) + (0,), version=version, product=PRODUCT,
        exe=EXE_NAME, exe_file=f"{EXE_NAME}.exe", copyright=COPYRIGHT), encoding="utf-8")
    spec = BUILD_DIR / f"{EXE_NAME}.spec"
    spec.write_text(SPEC_TEMPLATE.format(
        exclude=EXCLUDE_FILES, keep_qm=KEEP_TRANSLATIONS, entry=str(ENTRY), root=str(HERE),
        sprites=str(HERE / "miracle" / "sprites"), modules=EXCLUDE_MODULES, name=EXE_NAME,
        icon=str(ICON), version_file=str(version_file)), encoding="utf-8")
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
           "--distpath", str(HERE / "dist"), "--workpath", str(BUILD_DIR / "work"), str(spec)]
    print(f"{PRODUCT} {version} 빌드 중…", flush=True)
    rc = subprocess.call(cmd, cwd=HERE)
    if rc == 0:
        print(f"완료: {HERE / 'dist' / (EXE_NAME + '.exe')}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
