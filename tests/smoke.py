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
os.environ.update(APPDATA=str(TMP / "appdata"), MIRACLE_SPEED="0.04",
                  MIRACLE_MUTE="1", MIRACLE_NO_HOTKEY="1")      # 소리를 내지 않고, 전역 단축키도 진짜로 등록하지 않음
if os.environ.get("MIRACLE_SMOKE_SHOW") != "1":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import Qt, QTimer  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtWidgets import QApplication, QInputDialog, QMessageBox  # noqa: E402

from miracle import app as mapp  # noqa: E402
from miracle import core  # noqa: E402
from miracle import sound  # noqa: E402
from miracle import store as mstore  # noqa: E402
from miracle import stream  # noqa: E402

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
    check("룰렛 효과음 (틱 → 팡파르)", "spin" in sound.played and "fanfare" in sound.played
          and len(win.stage.wheel.ticks) >= 3, len(win.stage.wheel.ticks))
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


def t_core2() -> None:
    lad = core.ladder(6, 42)
    check("사다리: 1:1 대응", sorted(lad.end_of(s) for s in range(6)) == list(range(6)))
    check("사다리: 칸마다 가로줄", {c for _, c in lad.rungs} == set(range(5)))
    check("사다리 결과 칸 맞추기", core.ladder_results("", 3) == ["당첨", "꽝", "꽝"]
          and core.ladder_results("a\nb\nc\nd", 2) == ["a", "b"])
    t = core.teams(core.parse("\n".join("abcdefg")), 3, 1)
    check("팀: 인원 차이 1명 이하", max(len(m) for _, m in t) - min(len(m) for _, m in t) <= 1)
    check("팀이 사람보다 많으면 사람 수만큼", len(core.teams(core.parse("a\nb"), 5, 1)) == 2)
    check("순서: 모두 한 번씩", sorted(core.order(core.parse("a\nb\nc"), 3)) == ["a", "b", "c"])
    check("숫자 중복 없이 (범위보다 많이 달라면 범위만큼)",
          sorted(core.roll("number", 1, 10, lo=1, hi=3, unique=True)) == [1, 2, 3])
    check("주사위 요약", core.summary("dice", ["주사위 2d6", [3, 4]]) == "주사위 2d6: 3, 4 (합 7)")


LADDER_NAMES = ["레이무", "마리사", "사나에", "치르노", "사쿠야"]


def t_ladder() -> None:
    win.set_mode("ladder")
    win.editor.setPlainText("\n".join(LADDER_NAMES))
    win.ladder_text.setPlainText("당첨\n커피")
    lad = win.stage.ladder
    check("사다리 미리보기 (이름 · 결과 칸)", lad.top == LADDER_NAMES and lad.bottom == ["당첨", "커피", "꽝", "꽝", "꽝"]
          and lad.ladder is None)
    win.act()
    check("사다리 시작", lad.busy and "바로 결과" in win.go.text(), win.go.text())


def t_ladder2() -> None:
    d = store.history[0]
    ok = d.mode == "ladder" and len(d.result) == 5
    check("사다리 기록 (5명, 결과 1:1)", ok and [a for a, _ in d.result] == LADDER_NAMES
          and sorted(b for _, b in d.result) == sorted(["당첨", "커피", "꽝", "꽝", "꽝"]), d.result)
    if ok:
        lad = core.ladder(5, d.seed)
        bottom = core.ladder_results("당첨\n커피", 5)
        check("시드로 다시 해 봐도 같은 사다리", [[LADDER_NAMES[s], bottom[lad.end_of(s)]] for s in range(5)] == d.result)
    check("끝나면 버튼이 돌아옴", not win.busy and "기적을 일으키기" in win.go.text())
    n = len(store.history)
    win.act()
    win.act()                                              # 진행 중에 한 번 더 → 바로 결과
    check("진행 중 누르면 바로 결과", not win.stage.ladder.busy and len(store.history) == n + 1
          and len(win.stage.ladder.done_starts) == 5)


def t_teams() -> None:
    win.set_mode("teams")
    win.editor.setPlainText("\n".join(f"멤버{i}" for i in range(1, 12)))
    win.teams_count.setValue(3)
    win.teams_style.setCurrentIndex(1)
    check("팀 미리보기 (카드 3개)", len(win.stage.teams.teams) == 3)
    win.act()


def t_teams2() -> None:
    d = store.history[0]
    sizes = sorted(len(m) for _, m in d.result)
    check("팀 나누기 기록 (3팀 · 4·4·3명 · 중복 없음)", d.mode == "teams" and sizes == [3, 4, 4]
          and len({x for _, m in d.result for x in m}) == 11, d.result)
    check("동방 세력 팀 이름", all(t.endswith(" 팀") and t[:-2] in core.TEAM_NAMES["touhou"] for t, _ in d.result))
    again = [[t, list(m)] for t, m in core.teams(core.parse(d.text), 3, d.seed, "touhou")]
    check("시드로 다시 해 봐도 같은 팀", again == d.result)


def t_order() -> None:
    win.set_mode("order")
    win.editor.setPlainText("A\nB\nC\nD")
    win.act()


def t_order2() -> None:
    d = store.history[0]
    check("순서 정하기 기록", d.mode == "order" and sorted(d.result) == ["A", "B", "C", "D"], d.result)
    check("시드로 다시 해 봐도 같은 순서", core.order(core.parse(d.text), d.seed) == d.result)


def t_dice() -> None:
    win.set_mode("dice")
    win.dice_kind.setCurrentIndex(0)
    win.dice_count.setValue(3)
    win.dice_sides.setCurrentIndex(core.DICE_SIDES.index(6))
    check("주사위 옵션 (면 보이고 숫자 범위 숨김)", win.dice_sides.isVisibleTo(win) and not win.num_row.isVisibleTo(win))
    win.act()


def t_dice2() -> None:
    d = store.history[0]
    label, values = d.result
    check("주사위 3d6", d.mode == "dice" and label == "주사위 3d6" and len(values) == 3
          and all(1 <= v <= 6 for v in values), d.result)
    check("시드로 다시 해 봐도 같은 눈", core.roll("dice", d.seed, 3, 6) == values)
    check("합계 표시", "합" in win.result.text())
    win.dice_kind.setCurrentIndex(1)
    win.dice_count.setValue(1)
    win.act()


def t_dice3() -> None:
    d = store.history[0]
    check("동전 던지기", d.result[1][0] in ("앞", "뒤") and d.result[0] == "동전 1개", d.result)
    win.dice_kind.setCurrentIndex(2)
    check("숫자 옵션 (범위 보이고 면 숨김)", win.num_row.isVisibleTo(win) and not win.dice_sides.isVisibleTo(win))
    win.dice_count.setValue(5)
    win.num_lo.setValue(1)
    win.num_hi.setValue(5)
    win.num_unique.setChecked(True)
    win.act()


def t_dice4() -> None:
    d = store.history[0]
    check("숫자 1~5 다섯 개 (중복 없이)", sorted(d.result[1]) == [1, 2, 3, 4, 5], d.result)
    check("기록 탭 아이콘", "🎲" in win.hist.item(0).text())
    win.hist.setCurrentRow(0)
    win._copy_result()
    check("주사위 결과 복사", "숫자 1~5" in QGuiApplication.clipboard().text())
    win._save_settings()
    s2 = mstore.Store()
    check("새 옵션 저장", s2.settings.dice_kind == "number" and s2.settings.teams_count == 3
          and s2.settings.teams_style == "touhou" and s2.settings.ladder_results == "당첨\n커피")


def t_sound() -> None:
    import wave
    ok = True
    for name, secs in [*[(n, 1.0) for n in sound.STATIC], ("drumroll", 1.5), ("rattle", 1.6)]:
        path = sound.render(name, secs)
        with wave.open(str(path), "rb") as w:
            ok = ok and w.getframerate() == sound.RATE and w.getnframes() > sound.RATE * 0.08
    spin = sound.render("spin", 2.0, [0.1, 0.3, 0.6, 1.0])
    with wave.open(str(spin), "rb") as w:
        ok = ok and w.getnframes() >= sound.RATE * 2
    check("효과음 합성 (팡파르·딩·드럼롤·주사위·틱 …)", ok)
    check("효과음 기록 (당첨자 드럼롤 · 오류 머쓱)", "drumroll" in sound.played and "boop" in sound.played)


def t_stream() -> None:
    win.set_mode("wheel")
    win.bg_box.setCurrentIndex([k for k, _ in stream.BACKGROUNDS].index("magenta"))
    img = win.stage.grab().toImage()
    check("크로마키 배경 (자홍)", img.pixelColor(4, 4).name() == "#ff00ff", img.pixelColor(4, 4).name())
    win.bg_box.setCurrentIndex(0)
    win.toggle_stream()
    sw = win.stream_win
    check("방송 창 열기 (무대가 옮겨 감)", sw is not None and win.stage.parent() is sw and win.stage_placeholder.isVisible())
    win.toggle_stream()
    check("방송 창 닫기 (무대가 돌아옴)", win.stream_win is None and win.stage.parent() is not sw
          and not win.stage_placeholder.isVisible() and win.left.indexOf(win.stage) >= 0)
    win.hotkey_box.setCurrentIndex([k for k, _ in stream.HOTKEYS].index("ctrl_alt_m"))
    check("전역 단축키 선택", win.hotkey.key == "ctrl_alt_m" and "등록" in win.hotkey_state.text())
    import ctypes
    from ctypes import wintypes
    G["hot"] = 0
    real_cb = win.hotkey.filter.callback
    win.hotkey.filter.callback = lambda: G.__setitem__("hot", G["hot"] + 1)
    msg = wintypes.MSG()
    msg.message, msg.wParam = stream.WM_HOTKEY, stream.HOTKEY_ID
    took = win.hotkey.filter.nativeEventFilter(b"windows_generic_MSG", ctypes.addressof(msg))
    other = wintypes.MSG()
    other.message = 0x0100
    passed = win.hotkey.filter.nativeEventFilter(b"windows_generic_MSG", ctypes.addressof(other))
    check("전역 단축키 메시지만 받음", took[0] and not passed[0])
    G["real_cb"] = real_cb
    win.obs_on.setChecked(True)
    win.set_mode("dice")
    win.dice_kind.setCurrentIndex(0)
    win.dice_count.setValue(2)
    win.act()


def t_stream2() -> None:
    check("단축키를 누르면 기적 (콜백 호출)", G["hot"] == 1)
    win.hotkey.filter.callback = G["real_cb"]
    winner = stream.obs_dir() / "winner.txt"
    result = stream.obs_dir() / "result.txt"
    ok = winner.exists() and result.exists()
    text = winner.read_text(encoding="utf-8-sig") if ok else ""
    check("OBS 텍스트 파일 (winner · result)", ok and text.startswith("주사위 2d6") and "시드" in result.read_text(encoding="utf-8-sig"),
          text)
    win._save_settings()
    s2 = mstore.Store()
    check("방송 설정 저장", s2.settings.obs_text and s2.settings.hotkey == "ctrl_alt_m" and s2.settings.background == "sky")


def t_end() -> None:
    win.hotkey.clear()
    app.quit()


STEPS = [(t_core, 10), (t_core2, 10), (t_wheel, 700), (t_wheel2, 50), (t_raffle, 300), (t_raffle2, 1500),
         (t_raffle3, 1600), (t_raffle4, 50), (t_lists, 50), (t_persist, 50),
         (t_ladder, 900), (t_ladder2, 300), (t_teams, 700), (t_teams2, 50), (t_order, 600), (t_order2, 50),
         (t_dice, 400), (t_dice2, 400), (t_dice3, 400), (t_dice4, 50), (t_sound, 50), (t_stream, 500),
         (t_stream2, 50), (t_end, 0)]


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
