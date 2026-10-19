# -*- coding: utf-8 -*-
"""방송 모드: 크로마키 배경, 무대만 따로 띄우는 방송 창, 전역 단축키, OBS 텍스트 파일.

전역 단축키는 RegisterHotKey(창 없이, 스레드 단축키) — 어떤 키를 눌렀는지 읽지 않고, 정한 조합만 받는다.
MIRACLE_NO_HOTKEY=1 이면 실제로 등록하지 않는다 (시험용).
"""
from __future__ import annotations

import ctypes
import logging
import os
import sys
from ctypes import wintypes
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QAbstractNativeEventFilter, Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QVBoxLayout, QWidget

log = logging.getLogger("Miracle.stream")
BACKGROUNDS = (("sky", "하늘 (기본)"), ("magenta", "크로마키 자홍 #FF00FF"), ("blue", "크로마키 파랑 #0000FF"),
               ("green", "크로마키 초록 #00FF00"))
BG_COLORS = {"magenta": "#FF00FF", "blue": "#0000FF", "green": "#00FF00"}
HOTKEYS = (("off", "끄기"), ("ctrl_alt_m", "Ctrl + Alt + M"), ("ctrl_alt_space", "Ctrl + Alt + Space"), ("f9", "F9"))
_MOD_ALT, _MOD_CONTROL, _MOD_NOREPEAT = 0x1, 0x2, 0x4000
_KEYS = {"ctrl_alt_m": (_MOD_CONTROL | _MOD_ALT, 0x4D), "ctrl_alt_space": (_MOD_CONTROL | _MOD_ALT, 0x20),
         "f9": (0, 0x78)}
HOTKEY_ID = 0x5A4E
WM_HOTKEY = 0x0312


# ── 전역 단축키 ──
class HotkeyFilter(QAbstractNativeEventFilter):
    """WM_HOTKEY 를 받으면 callback (Qt 이벤트 루프가 꺼내는 모든 Windows 메시지 중에서)."""

    def __init__(self, callback: Callable[[], None]):
        super().__init__()
        self.callback = callback

    def nativeEventFilter(self, event_type, message):
        if bytes(event_type) in (b"windows_generic_MSG", b"windows_dispatcher_MSG"):
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                QTimer.singleShot(0, self.callback)
                return True, 0
        return False, 0


class Hotkey:
    def __init__(self, callback: Callable[[], None]):
        self.key = "off"
        self.ok = False
        self.filter = HotkeyFilter(callback)
        from PySide6.QtCore import QCoreApplication
        QCoreApplication.instance().installNativeEventFilter(self.filter)

    def set(self, key: str) -> bool:
        """단축키를 바꿈. 등록에 성공했으면(또는 끄기) True."""
        self.clear()
        self.key = key
        if key not in _KEYS:
            return True
        if sys.platform != "win32" or os.environ.get("MIRACLE_NO_HOTKEY") == "1":
            self.ok = True
            return True
        mods, vk = _KEYS[key]
        self.ok = bool(ctypes.windll.user32.RegisterHotKey(None, HOTKEY_ID, mods | _MOD_NOREPEAT, vk))
        log.info("전역 단축키 %s: %s", key, "등록" if self.ok else "실패 (다른 프로그램이 사용 중)")
        return self.ok

    def clear(self) -> None:
        if self.ok and self.key in _KEYS and sys.platform == "win32" and os.environ.get("MIRACLE_NO_HOTKEY") != "1":
            ctypes.windll.user32.UnregisterHotKey(None, HOTKEY_ID)
        self.ok = False


# ── OBS 텍스트 파일 ──
def obs_dir() -> Path:
    from .store import data_dir
    return data_dir() / "obs"


def write_obs(headline: str, detail: str) -> None:
    """OBS 텍스트 소스의 "파일에서 읽기" 용: winner.txt(한 줄 결과) · result.txt(자세히)."""
    d = obs_dir()
    d.mkdir(parents=True, exist_ok=True)
    for name, text in (("winner.txt", headline), ("result.txt", detail)):
        tmp = d / (name + ".tmp")
        tmp.write_text(text, encoding="utf-8-sig")
        os.replace(tmp, d / name)


# ── 방송 창 ──
class StreamWindow(QWidget):
    """무대만 크게 보여 주는 창 (OBS 창 캡처용). 조작은 원래 창에서, Space·F5 로도 진행."""

    def __init__(self, on_close: Callable[[], None], act: Callable[[], None]):
        super().__init__(None, Qt.Window)
        self.setWindowTitle("사나에의 기적 추첨기 — 방송 화면")
        self.on_close = on_close
        self.box = QVBoxLayout(self)
        self.box.setContentsMargins(0, 0, 0, 0)
        for keys in (Qt.Key_Space, "Ctrl+Return", "F5"):
            QShortcut(QKeySequence(keys), self, activated=act)
        self.resize(1280, 720)

    def closeEvent(self, e) -> None:
        self.on_close()
        super().closeEvent(e)
