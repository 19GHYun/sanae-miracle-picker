# -*- coding: utf-8 -*-
"""사나에의 기적 추첨기 시험 (smoke).

    python tests/smoke.py

- 저장은 임시 폴더(APPDATA)에 — 진짜 목록·기록은 건드리지 않는다.
- 기본은 화면에 아무것도 띄우지 않고(오프스크린) 돈다. 화면에 띄워 보려면 MIRACLE_SMOKE_SHOW=1.
- 연출은 MIRACLE_SPEED 로 빠르게.
끝나면 통과/실패를 출력하고, 실패가 있으면 종료 코드 1.
"""
from __future__ import annotations

import csv
import os
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TMP = Path(tempfile.mkdtemp(prefix="miracle_smoke_"))
os.environ.update(APPDATA=str(TMP / "appdata"), MIRACLE_SPEED="0.04")
if os.environ.get("MIRACLE_SMOKE_SHOW") != "1":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import Qt, QTimer  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtWidgets import QApplication, QInputDialog, QMessageBox  # noqa: E402

from miracle import app as mapp  # noqa: E402
from miracle import core  # noqa: E402
from miracle import store as mstore  # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []
G: dict = {}


def check(name: str, ok: bool, detail: object = "") -> None:
    RESULTS.append((name, bool(ok), str(detail)))
    print(("  ok  " if ok else "  FAIL") + f"  {name}  {detail}", flush=True)


def norm(result) -> list:
    return [[t, list(ns)] for t, ns in result]


# ── 추첨 로직 ──
def t_core() -> None:
    e = core.parse("a\nb x3\n\n# 주석\nc*2\nd x0\n")
    check("목록 읽기 (가중치·주석·x0)", [(x.name, x.weight) for x in e] == [("a", 1), ("b", 3), ("c", 2)])
    check("한 줄 쉼표", [x.name for x in core.parse("짜장, 짬뽕 ,볶음밥")] == ["짜장", "짬뽕", "볶음밥"])
    check("엑셀 붙여넣기 (탭)", [x.name for x in core.parse("a\tb\nc")] == ["a", "b", "c"])
    check("영문 이름은 가중치로 안 읽음", [(x.name, x.weight) for x in core.parse("FX3\nRex x2\n치킨x3")]
          == [("FX3", 1), ("Rex", 2), ("치킨", 3)])
    check("같은 시드 → 같은 룰렛 결과", core.spin(e, 12345) == core.spin(e, 12345))
    cnt = Counter(core.spin([core.Entry("a", 1), core.Entry("b", 3)], s)[0] for s in range(8000))
    ratio = cnt[1] / max(1, cnt[0])
    check("가중치 비율 1:3", 2.6 < ratio < 3.4, round(ratio, 2))
    people = core.parse("\n".join(f"p{i}" for i in range(10)))
    tiers = [core.Tier("1등", 1), core.Tier("2등", 3)]
    res = core.raffle(people, tiers, 7)
    names = [n for _, ns in res for n in ns]
    check("당첨자 뽑기: 인원 · 중복 없음", [len(ns) for _, ns in res] == [1, 3] and len(set(names)) == 4)
    check("같은 시드 → 같은 당첨자", core.raffle(people, tiers, 7) == res)
    check("한 사람은 한 번만 (응모권 여러 장이어도)",
          sorted(core.raffle(core.parse("a x5\nb"), [core.Tier("당첨", 2)], 3)[0][1]) == ["a", "b"])
    ex = core.raffle(core.parse("a\nb\nc"), [core.Tier("당첨", 3)], 5, exclude={"b"})
    check("빼고 뽑기", "b" not in ex[0][1] and len(ex[0][1]) == 2)
    short = core.raffle(core.parse("a\nb"), [core.Tier("1등", 1), core.Tier("2등", 5)], 9)
    check("사람이 모자라면 있는 만큼", [len(ns) for _, ns in short] == [1, 1])
    order = core.reveal_order(res)
    check("발표는 낮은 등수부터", order[0][0] == "2등" and order[-1][0] == "1등")


# ── 창 ──
def t_wheel() -> None:
    win.set_mode("wheel")
    win.editor.setPlainText("사나에\n레이무 x2\n마리사")
    check("항목 수 표시", "항목 3개" in win.count.text() and "가중치 합 4" in win.count.text(), win.count.text())
    win.remove_winner.setChecked(True)
    win.act()
    check("룰렛 돌기 시작", win.stage.wheel.spinning and not win.go.isEnabled())


def t_wheel2() -> None:
    d = store.history[0] if store.history else None
    ok = d is not None and d.mode == "wheel" and d.count == 3
    check("룰렛 결과 기록", ok and d.result[0] in ("사나에", "레이무", "마리사"), d.result if d else None)
    if ok:
        entries = core.parse(d.text)
        idx, _ = core.spin(entries, d.seed)
        check("시드로 다시 해 봐도 같은 결과", entries[idx].name == d.result[0])
        left = [x.name for x in core.parse(win.editor.toPlainText())]
        check("뽑힌 항목은 목록에서 빠짐", d.result[0] not in left and len(left) == 2, left)
    check("끝나면 버튼이 돌아옴", win.go.isEnabled() and not win.busy and "기적을 일으키기" in win.go.text())
    check("결과 줄", "결과" in win.result.text() and "시드" in win.result.text())
    win.editor.setPlainText("")
    win.act()
    check("빈 목록이면 사나에가 알려 줌", win.stage.sanae.mode == "oops" and not win.busy)


def t_raffle() -> None:
    win.set_mode("raffle")
    check("당첨자 뽑기 모드", win.stage.raffle.isVisible() and not win.stage.wheel.isVisible() and win.opts.currentIndex() == 1)
    win.editor.setPlainText("\n".join(f"참가자{i}" for i in range(1, 21)))
    while len(win.tier_rows) > 1:
        win._remove_tier(win.tier_rows[-1])
    win.tier_rows[0][1].setText("1등")
    win.tier_rows[0][2].setValue(1)
    win._add_tier("2등", 2)
    win._add_tier("3등", 3)
    win.auto.setChecked(False)
    win.exclude_last.setChecked(False)
    win.act()
    check("발표 시작", win.stage.raffle.phase == "rolling" and not win.go.isEnabled())


def t_raffle2() -> None:
    r = win.stage.raffle
    check("한 명 발표하고 기다림 (수동)", r.waiting and win.go.isEnabled() and "다음 발표" in win.go.text(), win.go.text())
    check("첫 발표는 3등", r.board.get("3등") and not r.board.get("1등"), r.board)
    win.act()                                              # 다음 발표 → 나머지는 자동으로
    r.auto = True


def t_raffle3() -> None:
    d = store.history[0] if store.history else None
    ok = d is not None and d.mode == "raffle"
    winners = [n for _, ns in d.result for n in ns] if ok else []
    check("당첨자 뽑기 기록 (1·2·3등 6명, 중복 없음)",
          ok and [len(ns) for _, ns in d.result] == [1, 2, 3] and len(set(winners)) == 6, d.result if d else None)
    if ok:
        again = core.raffle(core.parse(d.text), [core.Tier(t, len(ns)) for t, ns in d.result], d.seed)
        check("시드로 다시 해 봐도 같은 당첨자", norm(again) == norm(d.result))
    check("결과판에 6명", sum(len(v) for v in win.stage.raffle.board.values()) == 6)
    check("끝나면 버튼이 돌아옴", win.go.isEnabled() and not win.busy, win.go.text())
    G["prev"] = set(winners)
    win.exclude_last.setChecked(True)
    win.auto.setChecked(True)
    win.act()


def t_raffle4() -> None:
    d = store.history[0]
    winners = {n for _, ns in d.result for n in ns}
    check("직전 당첨자는 빼고 뽑기", d is not None and not (winners & G["prev"]) and len(winners) == 6, winners & G["prev"])


def t_lists() -> None:
    win.editor.setPlainText("가\n나\n다")
    real_get, real_q = QInputDialog.getText, QMessageBox.question
    QInputDialog.getText = staticmethod(lambda *a, **k: ("시험 목록", True))
    QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)
    win._save_as()
    check("새 이름으로 저장", store.lists.get("시험 목록") == "가\n나\n다" and win.list_box.currentText() == "시험 목록")
    win.editor.setPlainText("다른 글")
    win._load_list("시험 목록")
    check("목록 불러오기", win.editor.toPlainText() == "가\n나\n다")
    win.editor.setPlainText("b\na\nb\nc")
    win._dedupe()
    check("중복 제거", win.editor.toPlainText() == "b\na\nc")
    win._sort()
    check("가나다순", win.editor.toPlainText() == "a\nb\nc")
    win._shuffle()
    check("섞기 (항목은 그대로)", sorted(win.editor.toPlainText().split("\n")) == ["a", "b", "c"])
    win.list_box.setCurrentText("시험 목록")
    win._delete_list()
    check("목록 지우기", "시험 목록" not in store.lists)
    QInputDialog.getText, QMessageBox.question = real_get, real_q


def t_persist() -> None:
    win._save_settings()
    s2 = mstore.Store()
    check("설정 저장 · 다시 불러오기", s2.settings.mode == "raffle" and s2.settings.text == win.editor.toPlainText()
          and s2.settings.exclude_last and len(s2.history) == len(store.history), s2.settings.mode)
    check("기록 탭", win.hist.count() == len(store.history) and "시드" in win.hist.item(0).text())
    win.hist.setCurrentRow(0)
    win._copy_result()
    text = QGuiApplication.clipboard().text()
    check("결과 복사", "1등" in text and "시드" in text and "지문" in text, text.splitlines()[:2])
    out = TMP / "history.csv"
    store.export_csv(out)
    with open(out, encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    check("CSV 저장", rows[0][0] == "시각" and len(rows) == len(store.history) + 1)
    check("앱 아이콘", not mapp.app_icon().isNull())


def t_end() -> None:
    app.quit()


STEPS = [(t_core, 10), (t_wheel, 700), (t_wheel2, 50), (t_raffle, 300), (t_raffle2, 1500), (t_raffle3, 1600),
         (t_raffle4, 50), (t_lists, 50), (t_persist, 50), (t_end, 0)]


def run(i: int = 0) -> None:
    fn, wait = STEPS[i]
    try:
        fn()
    except Exception as e:  # 한 단계가 터져도 나머지는 계속
        check(f"{fn.__name__} 예외", False, repr(e))
    if i + 1 < len(STEPS):
        t = QTimer(app)
        t.setTimerType(Qt.PreciseTimer)
        t.setSingleShot(True)
        t.timeout.connect(lambda: run(i + 1))
        t.start(wait)


app = QApplication(sys.argv)
store = mstore.Store()
win = mapp.MainWindow(store)
win.show()
QTimer.singleShot(300, run)
app.exec()
fails = [r for r in RESULTS if not r[1]]
print(f"\n통과 {len(RESULTS) - len(fails)} / {len(RESULTS)}" + (f"   실패: {[r[0] for r in fails]}" if fails else ""),
      flush=True)
shutil.rmtree(TMP, ignore_errors=True)
os._exit(1 if fails else 0)
