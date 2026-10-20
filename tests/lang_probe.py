# -*- coding: utf-8 -*-
"""한 언어로 창을 띄워 보고 화면 글자에 한글이 남아 있지 않은지 본다 (smoke 가 ja · en 으로 따로 실행).

    python tests/lang_probe.py ja

화면에 띄우지 않고(오프스크린), 소리·전역 단축키 없이, 임시 폴더에서. 마지막 줄에 결과(JSON), 문제가 있으면 종료 코드 1.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

LANG = sys.argv[1] if len(sys.argv) > 1 else "ja"
ROOT = Path(__file__).resolve().parents[1]
TMP = Path(tempfile.mkdtemp(prefix=f"miracle_{LANG}_"))
os.environ.update(APPDATA=str(TMP), MIRACLE_LANG=LANG, MIRACLE_MUTE="1", MIRACLE_NO_HOTKEY="1", MIRACLE_SPEED="0.04")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import (QAbstractButton, QApplication, QComboBox, QLabel, QPlainTextEdit,  # noqa: E402
                               QSpinBox, QTabWidget, QWidget)

from miracle import app as mapp  # noqa: E402
from miracle import core, i18n, lineup, presets  # noqa: E402
from miracle.i18n import T  # noqa: E402
from miracle.store import Store  # noqa: E402

HANGUL = re.compile("[\uac00-\ud7a3]")
problems: list[str] = []


def no_hangul(where: str, text: str) -> None:
    if HANGUL.search(text or ""):
        problems.append(f"{where}: {text[:60]}")


qa = QApplication(sys.argv)
store = Store()
win = mapp.MainWindow(store)
win.show()
if i18n.lang() != LANG:
    problems.append(f"lang {i18n.lang()}")
if win.editor.toPlainText() != presets.LUNCH[LANG]:
    problems.append("first list is not this language's lunch menu")

# 화면의 모든 글자 (언어 선택칸의 '한국어' 는 빼고)
for w in win.findChildren(QWidget):
    if w is win.lang_box:
        continue
    no_hangul(type(w).__name__ + " tip", w.toolTip())
    if isinstance(w, (QLabel, QAbstractButton)):
        no_hangul(type(w).__name__, w.text())
    if isinstance(w, QComboBox):
        for i in range(w.count()):
            no_hangul("combo", w.itemText(i))
    if isinstance(w, QPlainTextEdit):
        no_hangul("placeholder", w.placeholderText())
        no_hangul("editor", w.toPlainText())
    if isinstance(w, QSpinBox):
        no_hangul("suffix", w.suffix())
    if isinstance(w, QTabWidget):
        for i in range(w.count()):
            no_hangul("tab", w.tabText(i))
no_hangul("title", win.windowTitle())

# 모드마다 무대를 그려 보고, 진행 중인 것은 바로 결과로 → 기록 · 결과 줄 · 복사 글
names = presets.presets(LANG)
chars = list(names.values())[0].split("\n")
for mode in mapp.MODE_KEYS:
    win.set_mode(mode)
    win.stage.grab()
    if mode in ("ladder", "teams", "order"):
        win.editor.setPlainText("\n".join(chars[:5]))
        win.teams_style.setCurrentIndex(2)
        win.act()
    elif mode == "dice":
        for kind in range(3):
            win.dice_kind.setCurrentIndex(kind)
            win.dice_count.setValue(2)
            win.act()
            win.stage.grab()
            win.act()
            no_hangul("result dice", win.result.text())
            no_hangul("history dice", win.draw_text(store.history[0]))
        continue
    elif mode == "gacha":
        win._gacha_sample()
        win.act()
    else:
        continue
    win.stage.grab()
    win.act()                                              # 진행 중 → 바로 결과
    win.stage.grab()
    if store.history and store.history[0].mode == mode:
        no_hangul("result " + mode, win.result.text())
        no_hangul("history " + mode, win.draw_text(store.history[0]))
        no_hangul("headline " + mode, core.headline(mode, store.history[0].result))
    else:
        problems.append(f"no record for {mode}")
    no_hangul("sanae " + mode, win.stage.sanae.bubble)
no_hangul("history list", "\n".join(win.hist.item(i).text() for i in range(win.hist.count())))
from miracle.cameo import GODS  # noqa: E402
for _color, lines in GODS.values():                        # 신님 대사
    for line in lines:
        no_hangul("cameo", line)
win.stage.cameo.play()
win.stage.cameo.started -= win.stage.cameo.length * 0.5
win.stage.grab()

teams = core.team_names(2, "color")
checks = {
    "team names": not HANGUL.search(" ".join(teams + core.team_names(3, "touhou") + core.team_names(2))),
    "team color": lineup.team_color(teams[0], 5).name() == lineup.NAMED_COLORS["빨강"].lower(),
    "blank": core.is_blank(core.ladder_results("", 2)[1]) and not core.is_blank(T("당첨")),
    "coin": core.roll("coin", 1)[0] in (T("앞"), T("뒤")),
    "dice sum": core.summary("dice", [core.dice_label("dice", 2, 6, 1, 1), [3, 4]]).endswith(T(" (합 {total})", total=7)),
    "mode name": not HANGUL.search(core.mode_name("gacha")),
}
problems += [k for k, ok in checks.items() if not ok]
out = {"lang": LANG, "title": win.windowTitle(), "go": win.go.text(), "teams": teams, "problems": problems}
win.close()
shutil.rmtree(TMP, ignore_errors=True)
print(json.dumps(out))
sys.exit(1 if problems else 0)
