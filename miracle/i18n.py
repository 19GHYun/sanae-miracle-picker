# -*- coding: utf-8 -*-
"""언어: 한국어(원문) · 日本語 · English.

화면 글자는 T("한국어 원문") 으로 감싸고, 번역 표(i18n_ja.py · i18n_en.py)에서 찾는다 (없으면 원문 그대로).
언어는 이 모듈을 처음 불러올 때 정해진다 (설정 → 없으면 시스템 언어). 바꾸면 다시 시작해야 적용.
  MIRACLE_LANG=ko|ja|en   강제로 (시험용)
"""
from __future__ import annotations

import json
import os

LANGS = (("auto", "자동"), ("ko", "한국어"), ("ja", "日本語"), ("en", "English"))
FONTS = {"ko": "Malgun Gothic", "ja": "Yu Gothic UI", "en": "Segoe UI"}    # 없는 글자는 Qt 가 다른 글꼴로 채움
_lang = "ko"
_table: dict[str, str] = {}


def _system() -> str:
    try:
        from PySide6.QtCore import QLocale
        name = QLocale.system().name().lower()
    except ImportError:
        name = ""
    if name.startswith("ko"):
        return "ko"
    if name.startswith("ja"):
        return "ja"
    return "en"


def _saved() -> str:
    from .store import data_dir
    try:
        return json.loads((data_dir() / "settings.json").read_text(encoding="utf-8")).get("lang", "auto")
    except (OSError, ValueError):
        return "auto"


def set_lang(code: str) -> str:
    global _lang, _table
    if code not in ("ko", "ja", "en"):
        code = _system()
    _lang = code
    if code == "ja":
        from .i18n_ja import TABLE
    elif code == "en":
        from .i18n_en import TABLE
    else:
        TABLE = {}
    _table = TABLE
    return code


def lang() -> str:
    return _lang


def font() -> str:
    """이 언어의 화면 글꼴 (한국어 글꼴로 일본어를 쓰면 가나 사이가 벌어져 보임)."""
    return FONTS[_lang]


def T(text: str, **kw) -> str:
    """번역 (원문 = 한국어). kw 가 있으면 {이름} 자리를 채움."""
    s = _table.get(text, text)
    return s.format(**kw) if kw else s


set_lang(os.environ.get("MIRACLE_LANG") or _saved())
