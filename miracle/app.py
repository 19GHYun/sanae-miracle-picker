# -*- coding: utf-8 -*-
"""사나에의 기적 추첨기 — 메인 창.

  MIRACLE_SPEED=0.05   연출 시간 배율 (시험용으로 빠르게)
"""
from __future__ import annotations

import ctypes
import logging
import os
import random
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PySide6.QtCore import QByteArray, QPointF, QRect, QRectF, Qt, QTimer
from PySide6.QtGui import (QColor, QGuiApplication, QIcon, QKeySequence, QLinearGradient, QPainter,
                           QPainterPath, QPen, QPixmap, QShortcut)
from PySide6.QtWidgets import (QApplication, QButtonGroup, QCheckBox, QComboBox, QFileDialog, QHBoxLayout,
                               QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
                               QMessageBox, QPlainTextEdit, QPushButton, QSpinBox, QStackedWidget, QTabWidget,
                               QVBoxLayout, QWidget)

from . import __version__, core
from .cutin import MiracleCutIn
from .raffle import RaffleStage
from .sanae import IDLE_LINES, SPIN_LINES, SanaeWidget, Sprites
from .store import Draw, Store, data_dir, now_text
from .wheel import WheelWidget

log = logging.getLogger("Miracle")
TITLE = "사나에의 기적 추첨기"
SPEED = float(os.environ.get("MIRACLE_SPEED") or 1.0)
WHEEL_SECONDS = 5.5
MODES = (("wheel", "🎡  룰렛"), ("raffle", "🎫  당첨자 뽑기"))
STYLE = """
QWidget#root { background: #F2FAF4; }
QLabel { font-family: 'Malgun Gothic'; color: #22352A; }
QLabel#hint { color: #6B7F72; font-size: 11px; }
QLabel#result { font-size: 13px; padding: 2px 4px; }
QPushButton { font-family: 'Malgun Gothic'; font-size: 12px; }
QPushButton#mode { background: #FFFFFF; color: #2E6B48; border: 1px solid #B9DEC6; border-radius: 16px;
                   padding: 7px 18px; font-weight: 700; font-size: 13px; }
QPushButton#mode:checked { background: #2E9E5B; color: #FFFFFF; border-color: #2E9E5B; }
QPushButton#mode:disabled { color: #9FBFAE; }
QPushButton#go { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2E9E5B, stop:1 #3D5BA9);
                 color: #FFFFFF; border: none; border-radius: 14px; font-size: 19px; font-weight: 800; }
QPushButton#go:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #37B068, stop:1 #4A69BA); }
QPushButton#go:disabled { background: #9FBFAE; }
QPushButton#small { background: #FFFFFF; color: #2E6B48; border: 1px solid #B9DEC6; border-radius: 8px; padding: 4px 9px; }
QPushButton#small:hover { background: #E6F5EA; }
QTabWidget#side::pane { background: #FFFFFF; border: 1px solid #CFE7D7; border-radius: 12px; }
QTabBar::tab { background: transparent; padding: 8px 14px; font-family: 'Malgun Gothic'; font-weight: 700;
               font-size: 13px; color: #6B7F72; }
QTabBar::tab:selected { color: #2E9E5B; border-bottom: 2px solid #2E9E5B; }
QPlainTextEdit, QListWidget, QLineEdit, QSpinBox, QComboBox { background: #FBFEFC; border: 1px solid #CFE7D7;
    border-radius: 8px; font-family: 'Malgun Gothic'; font-size: 13px; padding: 3px; color: #22352A; }
QListWidget::item { padding: 4px 2px; border-bottom: 1px solid #EEF6F0; }
QListWidget::item:selected { background: #DFF2E5; color: #22352A; }
QCheckBox { font-family: 'Malgun Gothic'; font-size: 12px; color: #22352A; }
"""


def app_icon() -> QIcon:
    """앱 아이콘: 초록·파랑 둥근 네모 위에 사나에 얼굴."""
    s = 256
    pm = QPixmap(s, s)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    g = QLinearGradient(0, 0, s, s)
    g.setColorAt(0, QColor("#2E9E5B"))
    g.setColorAt(1, QColor("#3D5BA9"))
    p.setPen(Qt.NoPen)
    p.setBrush(g)
    p.drawRoundedRect(QRectF(8, 8, s - 16, s - 16), 52, 52)
    p.setBrush(QColor(255, 255, 255, 235))
    p.drawEllipse(QPointF(s / 2, s / 2 + 6), 98, 98)
    try:
        sp = Sprites("sanae")
        img, _ = sp.frames["idle_0"]
        head = img.copy(0, 0, img.width(), int(img.height() * 0.62))   # 얼굴 쪽
        k = 200 / head.width()
        p.drawImage(QRectF(s / 2 - head.width() * k / 2, 30, head.width() * k, head.height() * k), head)
    except (OSError, KeyError, ValueError):
        pass
    p.end()
    return QIcon(pm)


class Stage(QWidget):
    """추첨 무대: 하늘 배경 + 룰렛/당첨자 뽑기 + 사나에 + 컷인."""

    LEFT = 220          # 사나에 자리

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setMinimumSize(580, 430)
        self.wheel = WheelWidget(self)
        self.raffle = RaffleStage(self)
        self.sanae = SanaeWidget(self)
        self.cutin = MiracleCutIn(self)
        self.mode = "wheel"

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self.wheel.setVisible(mode == "wheel")
        self.raffle.setVisible(mode == "raffle")
        self._layout()

    def resizeEvent(self, _e) -> None:
        self._layout()

    def _layout(self) -> None:
        w, h = self.width(), self.height()
        area = QRect(self.LEFT, 6, max(200, w - self.LEFT - 10), h - 12)
        self.wheel.setGeometry(area)
        self.raffle.setGeometry(area)
        self.sanae.move(-30, h - self.sanae.height() + 2)
        self.sanae.raise_()
        if self.cutin.isVisible():
            self.cutin.setGeometry(self.rect())
            self.cutin.raise_()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(r, 18, 18)
        g = QLinearGradient(0, 0, 0, r.height())
        g.setColorAt(0, QColor("#D8EFFF"))
        g.setColorAt(0.7, QColor("#F2FBF4"))
        g.setColorAt(1, QColor("#E2F2E0"))
        p.fillPath(path, g)
        p.setClipPath(path)
        p.setPen(QPen(QColor(255, 255, 255, 160), 2.2, Qt.SolidLine, Qt.RoundCap))   # 모리야의 바람
        for i, (x, y) in enumerate(((0.12, 0.16), (0.55, 0.1), (0.82, 0.24), (0.3, 0.32))):
            cx, cy = r.width() * x, r.height() * y
            wind = QPainterPath(QPointF(cx - 60, cy))
            wind.cubicTo(cx - 20, cy - 18, cx + 20, cy + 14, cx + 52, cy - 4)
            wind.arcTo(QRectF(cx + 40, cy - 16, 22, 22), 270, 250)
            p.drawPath(wind)
        hill = QPainterPath(QPointF(0, r.height()))
        hill.lineTo(0, r.height() * 0.86)
        hill.cubicTo(r.width() * 0.3, r.height() * 0.78, r.width() * 0.6, r.height() * 0.93, r.width(), r.height() * 0.82)
        hill.lineTo(r.width(), r.height())
        hill.closeSubpath()
        p.setPen(Qt.NoPen)
        p.fillPath(hill, QColor("#CDE9CB"))
        p.setClipping(False)
        p.setPen(QPen(QColor("#B9DEC6"), 1.2))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)
        p.end()


class MainWindow(QMainWindow):
    def __init__(self, store: Store):
        super().__init__()
        self.store = store
        s = store.settings
        self.mode = s.mode if s.mode in dict(MODES) else "wheel"
        self._programmatic = False
        self._pending: tuple | None = None
        self.setWindowTitle(f"{TITLE}  v{__version__}")
        self.setWindowIcon(app_icon())
        self.setStyleSheet(STYLE)
        root = QWidget(objectName="root")
        self.setCentralWidget(root)
        h = QHBoxLayout(root)
        h.setContentsMargins(14, 14, 14, 14)
        h.setSpacing(14)
        left = QVBoxLayout()
        left.setSpacing(10)
        h.addLayout(left, 1)
        bar = QHBoxLayout()
        self.mode_btns: dict[str, QPushButton] = {}
        group = QButtonGroup(self)
        for key, text in MODES:
            b = QPushButton(text, objectName="mode")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, key=key: self.set_mode(key))
            group.addButton(b)
            bar.addWidget(b)
            self.mode_btns[key] = b
        bar.addStretch(1)
        bar.addWidget(QLabel("사다리·팀 나누기·순서 정하기·주사위는 곧 나와요", objectName="hint"))
        left.addLayout(bar)
        self.stage = Stage(root)
        left.addWidget(self.stage, 1)
        self.go = QPushButton(objectName="go")
        self.go.setCursor(Qt.PointingHandCursor)
        self.go.setMinimumHeight(56)
        self.go.clicked.connect(self.act)
        left.addWidget(self.go)
        self.result = QLabel(objectName="result")
        self.result.setWordWrap(True)
        self.result.setTextInteractionFlags(Qt.TextSelectableByMouse)
        left.addWidget(self.result)
        self.tabs = QTabWidget(objectName="side")
        self.tabs.setFixedWidth(350)
        self.tabs.addTab(self._list_tab(), "📝 목록")
        self.tabs.addTab(self._history_tab(), "📜 기록")
        h.addWidget(self.tabs)
        for keys in (Qt.Key_Space, "Ctrl+Return", "F5"):
            QShortcut(QKeySequence(keys), self, activated=self.act)
        self._save_timer = QTimer(self, singleShot=True, interval=600, timeout=self._save_settings)
        self.resize(1100, 740)
        if s.geometry:
            self.restoreGeometry(QByteArray.fromHex(s.geometry.encode()))
        self.set_mode(self.mode)
        self._text_changed()
        self._refresh_history()
        self.result.setText("오른쪽에 목록을 적고 <b>✨ 기적을 일으키기!</b> (또는 Space)")
        self.stage.sanae.say(random.choice(IDLE_LINES), 4.0)

    # ── 오른쪽: 목록 ──
    def _list_tab(self) -> QWidget:
        s = self.store.settings
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(7)
        row = QHBoxLayout()
        self.list_box = QComboBox()
        self.list_box.setToolTip("저장해 둔 목록")
        self.list_box.activated.connect(lambda _i: self._load_list(self.list_box.currentText()))
        row.addWidget(self.list_box, 1)
        for text, tip, fn in (("💾", "이 이름으로 저장 (덮어쓰기)", self._save_list), ("＋", "새 이름으로 저장", self._save_as),
                              ("✕", "이 목록 지우기", self._delete_list)):
            b = QPushButton(text, objectName="small")
            b.setToolTip(tip)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(fn)
            row.addWidget(b)
        v.addLayout(row)
        self._fill_lists(s.list_name)
        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText("한 줄에 하나씩 적어 주세요\n\n사나에\n레이무 x2   ← 두 배로 잘 뽑혀요\n마리사\n\n"
                                       "엑셀에서 복사해 붙여도 되고,\n한 줄에 쉼표로 적어도 돼요 (짜장, 짬뽕, 볶음밥)")
        self.editor.setPlainText(s.text)
        self.editor.textChanged.connect(self._text_changed)
        v.addWidget(self.editor, 1)
        self.count = QLabel(objectName="hint")
        v.addWidget(self.count)
        tools = QHBoxLayout()
        for text, fn in (("🔀 섞기", self._shuffle), ("가나다순", self._sort), ("중복 제거", self._dedupe)):
            b = QPushButton(text, objectName="small")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(fn)
            tools.addWidget(b)
        tools.addStretch(1)
        v.addLayout(tools)
        self.opts = QStackedWidget()
        wheel_opts = QWidget()
        wv = QVBoxLayout(wheel_opts)
        wv.setContentsMargins(0, 6, 0, 0)
        self.remove_winner = QCheckBox("뽑힌 항목은 목록에서 빼기")
        self.remove_winner.setChecked(s.remove_winner)
        self.remove_winner.toggled.connect(self._queue_save)
        wv.addWidget(self.remove_winner)
        wv.addStretch(1)
        self.opts.addWidget(wheel_opts)
        self.opts.addWidget(self._raffle_opts())
        v.addWidget(self.opts)
        return w

    def _raffle_opts(self) -> QWidget:
        s = self.store.settings
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 6, 0, 0)
        v.setSpacing(5)
        v.addWidget(QLabel("<b>등수</b>  (위에서부터 1등 · 발표는 아래 등수부터)"))
        self.tier_box = QVBoxLayout()
        self.tier_box.setSpacing(4)
        v.addLayout(self.tier_box)
        self.tier_rows: list[tuple[QWidget, QLineEdit, QSpinBox]] = []
        for name, count in s.tiers or [["당첨", 1]]:
            self._add_tier(name, count)
        add = QPushButton("＋ 등수 추가", objectName="small")
        add.setCursor(Qt.PointingHandCursor)
        add.clicked.connect(lambda: (self._add_tier(f"{len(self.tier_rows) + 1}등", 1), self._queue_save()))
        v.addWidget(add, 0, Qt.AlignLeft)
        self.unique = QCheckBox("한 사람은 한 번만 당첨")
        self.unique.setChecked(s.unique)
        self.exclude_last = QCheckBox("직전 추첨 당첨자는 빼고 뽑기")
        self.exclude_last.setChecked(s.exclude_last)
        self.auto = QCheckBox("자동으로 계속 발표 (끄면 한 명씩 버튼으로)")
        self.auto.setChecked(s.auto_reveal)
        for c in (self.unique, self.exclude_last, self.auto):
            c.toggled.connect(self._queue_save)
            v.addWidget(c)
        return w

    def _add_tier(self, name: str, count: int) -> None:
        roww = QWidget()
        h = QHBoxLayout(roww)
        h.setContentsMargins(0, 0, 0, 0)
        edit = QLineEdit(name)
        edit.setMaxLength(20)
        spin = QSpinBox()
        spin.setRange(0, 999)
        spin.setValue(int(count))
        spin.setSuffix(" 명")
        rm = QPushButton("✕", objectName="small")
        rm.setCursor(Qt.PointingHandCursor)
        rm.setToolTip("이 등수 빼기")
        entry = (roww, edit, spin)
        rm.clicked.connect(lambda: self._remove_tier(entry))
        edit.textChanged.connect(self._queue_save)
        spin.valueChanged.connect(self._queue_save)
        h.addWidget(edit, 1)
        h.addWidget(spin)
        h.addWidget(rm)
        self.tier_box.addWidget(roww)
        self.tier_rows.append(entry)

    def _remove_tier(self, entry) -> None:
        if len(self.tier_rows) <= 1:
            return
        self.tier_rows.remove(entry)
        entry[0].deleteLater()
        self._queue_save()

    def tiers(self) -> list[core.Tier]:
        out = []
        for i, (_, edit, spin) in enumerate(self.tier_rows):
            name = edit.text().strip() or f"{i + 1}등"
            if spin.value() > 0:
                out.append(core.Tier(name, spin.value()))
        return out

    # ── 오른쪽: 기록 ──
    def _history_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(12, 12, 12, 12)
        self.hist = QListWidget()
        self.hist.setWordWrap(True)
        v.addWidget(self.hist, 1)
        row = QHBoxLayout()
        for text, fn in (("📋 결과 복사", self._copy_result), ("💾 CSV 저장", self._export_csv), ("기록 지우기", self._clear_history)):
            b = QPushButton(text, objectName="small")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(fn)
            row.addWidget(b)
        v.addLayout(row)
        tip = QLabel("모든 추첨은 시드로 정해져요. 같은 목록·같은 시드면 언제 다시 해도 같은 결과예요 "
                     "(목록 지문으로 같은 목록이었는지 확인).", objectName="hint")
        tip.setWordWrap(True)
        v.addWidget(tip)
        return w

    def _refresh_history(self) -> None:
        self.hist.clear()
        for d in self.store.history[:200]:
            icon = "🎡" if d.mode == "wheel" else "🎫"
            item = QListWidgetItem(f"{d.when[5:16].replace('T', ' ')}  {icon} {d.title}  ({d.count}개)\n"
                                   f"→ {core.summary(d.mode, d.result)}\n   시드 {core.seed_text(d.seed)} · 지문 {d.print_}")
            item.setData(Qt.UserRole, d)
            self.hist.addItem(item)

    def draw_text(self, d: Draw) -> str:
        lines = [f"[{TITLE}] {d.when.replace('T', ' ')}",
                 f"{'룰렛' if d.mode == 'wheel' else '당첨자 뽑기'} · 목록: {d.title} ({d.count}개)"]
        if d.mode == "wheel":
            lines.append(f"결과: {d.result[0]}")
        else:
            lines += [f"{tier}: {', '.join(names) if names else '없음'}" for tier, names in d.result]
        lines.append(f"시드 {core.seed_text(d.seed)} · 목록 지문 {d.print_}")
        return "\n".join(lines)

    def _copy_result(self) -> None:
        item = self.hist.currentItem() or self.hist.item(0)
        if item is None:
            return
        QGuiApplication.clipboard().setText(self.draw_text(item.data(Qt.UserRole)))
        self.stage.sanae.say("결과를 복사했어요!", 2.0)

    def _export_csv(self) -> None:
        if not self.store.history:
            return
        path, _ = QFileDialog.getSaveFileName(self, "기록을 CSV로 저장", str(Path.home() / "Desktop" / "기적추첨_기록.csv"),
                                              "CSV (*.csv)")
        if path:
            self.store.export_csv(Path(path))
            self.stage.sanae.say("기록을 저장했어요!", 2.0)

    def _clear_history(self) -> None:
        if self.store.history and QMessageBox.question(self, TITLE, "기록을 모두 지울까요?") == QMessageBox.Yes:
            self.store.clear_history()
            self._refresh_history()

    # ── 목록 다루기 ──
    def _fill_lists(self, current: str) -> None:
        self.list_box.blockSignals(True)
        self.list_box.clear()
        self.list_box.addItems(list(self.store.lists))
        if current in self.store.lists:
            self.list_box.setCurrentText(current)
        else:
            self.list_box.setCurrentIndex(-1)
            self.list_box.setPlaceholderText("(저장 안 한 목록)")
        self.list_box.blockSignals(False)

    def _load_list(self, name: str) -> None:
        if self.busy or name not in self.store.lists:
            return
        self.editor.setPlainText(self.store.lists[name])
        self.store.settings.list_name = name
        self._queue_save()

    def _save_list(self) -> None:
        name = self.list_box.currentText()
        if not name:
            self._save_as()
            return
        self.store.save_list(name, self.editor.toPlainText())
        self.stage.sanae.say(f"「{name}」 저장했어요!", 2.0)

    def _save_as(self) -> None:
        name, ok = QInputDialog.getText(self, TITLE, "새 목록 이름")
        name = name.strip()
        if ok and name:
            self.store.save_list(name, self.editor.toPlainText())
            self.store.settings.list_name = name
            self._fill_lists(name)
            self._queue_save()
            self.stage.sanae.say(f"「{name}」 저장했어요!", 2.0)

    def _delete_list(self) -> None:
        name = self.list_box.currentText()
        if name and QMessageBox.question(self, TITLE, f"「{name}」 목록을 지울까요?") == QMessageBox.Yes:
            self.store.delete_list(name)
            self._fill_lists("")

    def _set_text(self, text: str, keep_wheel: bool = False) -> None:
        self._programmatic = keep_wheel
        self.editor.setPlainText(text)
        self._programmatic = False

    def _lines(self) -> list[str]:
        return [ln for ln in self.editor.toPlainText().split("\n") if ln.strip()]

    def _shuffle(self) -> None:
        lines = self._lines()
        random.shuffle(lines)
        self._set_text("\n".join(lines))

    def _sort(self) -> None:
        self._set_text("\n".join(sorted(self._lines(), key=str.casefold)))

    def _dedupe(self) -> None:
        seen, out = set(), []
        for ln in self._lines():
            if ln.strip() not in seen:
                seen.add(ln.strip())
                out.append(ln)
        self._set_text("\n".join(out))

    def _text_changed(self) -> None:
        entries = core.parse(self.editor.toPlainText())
        total = core.total_weight(entries)
        self.count.setText(f"항목 {len(entries)}개" + (f" · 가중치 합 {total}" if total != len(entries) else "")
                           + "   ·   한 줄에 하나, '이름 x3' = 세 배")
        if not self._programmatic:
            self.stage.wheel.set_entries(entries)
        self._queue_save()

    # ── 모드 ──
    def set_mode(self, mode: str) -> None:
        if self.busy:
            self.mode_btns[self.mode].setChecked(True)
            return
        self.mode = mode
        self.mode_btns[mode].setChecked(True)
        self.stage.set_mode(mode)
        self.opts.setCurrentIndex(0 if mode == "wheel" else 1)
        self._update_go()
        self._queue_save()

    @property
    def busy(self) -> bool:
        r = self.stage.raffle
        return self.stage.wheel.spinning or r.phase == "rolling" or r.waiting

    def _update_go(self) -> None:
        r = self.stage.raffle
        if self.stage.wheel.spinning or r.phase == "rolling":
            self.go.setText("기적이 일어나는 중…")
            self.go.setEnabled(False)
        elif r.waiting and not r.auto:
            self.go.setText(f"다음 발표 ▶   ({r.done_count} / {r._total})")
            self.go.setEnabled(True)
        elif r.waiting:
            self.go.setText("발표 중…")
            self.go.setEnabled(False)
        else:
            self.go.setText("✨ 기적을 일으키기!   (Space)")
            self.go.setEnabled(True)
        for b in self.mode_btns.values():
            b.setEnabled(not self.busy)

    # ── 추첨 ──
    def act(self) -> None:
        if self.stage.cutin.active:
            self.stage.cutin.finish()
        r = self.stage.raffle
        if r.waiting and not r.auto:
            self.stage.sanae.set_mode("spin", "다음은…!", 1.5)
            r.next()
            self._update_go()
            return
        if self.busy:
            return
        entries = core.parse(self.editor.toPlainText())
        if self.mode == "wheel":
            self._spin(entries)
        else:
            self._draw(entries)

    def _title(self) -> str:
        name = self.list_box.currentText()
        if name and self.store.lists.get(name, "").strip() == self.editor.toPlainText().strip():
            return name
        return f"{name} (고침)" if name else "저장 안 한 목록"

    def _spin(self, entries: list[core.Entry]) -> None:
        if not entries:
            self.stage.sanae.set_mode("oops", "목록이 비어 있어요! 오른쪽에 적어 주세요.", 3.0)
            return
        seed = core.new_seed()
        idx, frac = core.spin(entries, seed)
        self.stage.wheel.set_entries(entries)
        self.stage.sanae.set_mode("spin", random.choice(SPIN_LINES), 2.5)
        self.stage.wheel.spin_to(idx, frac, WHEEL_SECONDS * SPEED, lambda i: self._spun(entries, i, seed))
        self._update_go()
        log.info("룰렛: %d개, 시드 %s", len(entries), core.seed_text(seed))

    def _spun(self, entries: list[core.Entry], idx: int, seed: int) -> None:
        name = entries[idx].name
        text = self.editor.toPlainText()
        d = Draw(now_text(), "wheel", self._title(), len(entries), seed, core.fingerprint(entries), [name], text)
        self.store.add(d)
        self._refresh_history()
        self.stage.sanae.set_mode("happy", f"「{name}」! 기적이에요!", 5.5)
        self.stage.cutin.play("✨ 기적 발생! ✨", name, SPEED, hide=self.stage.sanae)
        self.result.setText(f"🎡 결과: <b>{name}</b>   ·   {len(entries)}개 중   ·   시드 {core.seed_text(seed)}")
        if self.remove_winner.isChecked():                       # 뽑힌 줄 하나 빼기 (바퀴는 다음에 돌릴 때 바뀜)
            lines = text.split("\n")
            for i, ln in enumerate(lines):
                got = core.parse(ln)
                if got and got[0].name == name:
                    del lines[i]
                    break
            self._set_text("\n".join(lines), keep_wheel=True)
        self._update_go()
        log.info("룰렛 결과: %s", name)

    def _last_winners(self) -> set[str]:
        for d in self.store.history:
            if d.mode == "raffle":
                return {n for _, names in d.result for n in names}
        return set()

    def _draw(self, entries: list[core.Entry]) -> None:
        tiers = self.tiers()
        if not entries or not tiers:
            self.stage.sanae.set_mode("oops", "목록이나 등수가 비어 있어요!" if not entries else "등수의 인원을 정해 주세요!", 3.0)
            return
        exclude = self._last_winners() if self.exclude_last.isChecked() else set()
        seed = core.new_seed()
        results = core.raffle(entries, tiers, seed, self.unique.isChecked(), exclude)
        order = core.reveal_order(results)
        if not order:
            self.stage.sanae.set_mode("oops", "뽑을 수 있는 사람이 없어요…", 3.0)
            return
        self._pending = (entries, results, seed, self.editor.toPlainText())
        self.stage.sanae.set_mode("spin", "누가 뽑힐까요…!", 2.0)
        self.stage.raffle.start(results, order, [e.name for e in entries], self._revealed, self._raffle_done,
                                auto=self.auto.isChecked(), speed=SPEED)
        self._update_go()
        log.info("당첨자 뽑기: %d명, 등수 %s, 시드 %s", len(entries), [(t.name, t.count) for t in tiers], core.seed_text(seed))

    def _revealed(self, tier: str, name: str, n: int, total: int) -> None:
        if n == total:
            self.stage.cutin.play(f"✨ {tier} — 기적 발생! ✨", name, SPEED, hide=self.stage.sanae)
            self.stage.sanae.set_mode("happy", f"{tier}은(는) 「{name}」! 축하해요!", 4.0)
        else:
            self.stage.sanae.set_mode("happy", f"{tier}: 「{name}」!", 2.5)
        self._update_go()

    def _raffle_done(self) -> None:
        entries, results, seed, text = self._pending
        d = Draw(now_text(), "raffle", self._title(), len(entries), seed, core.fingerprint(entries), results, text)
        self.store.add(d)
        self._refresh_history()
        self.result.setText(f"🎫 {core.summary('raffle', results)}   ·   {len(entries)}명 중   ·   시드 {core.seed_text(seed)}")
        QTimer.singleShot(0, self._update_go)
        log.info("당첨자 뽑기 결과: %s", core.summary("raffle", results))

    # ── 설정 저장 ──
    def _queue_save(self, *_a) -> None:
        self._save_timer.start()

    def _save_settings(self) -> None:
        s = self.store.settings
        s.mode = self.mode
        s.text = self.editor.toPlainText()
        s.list_name = self.list_box.currentText()
        s.remove_winner = self.remove_winner.isChecked()
        s.unique = self.unique.isChecked()
        s.exclude_last = self.exclude_last.isChecked()
        s.auto_reveal = self.auto.isChecked()
        s.tiers = [[edit.text(), spin.value()] for _, edit, spin in self.tier_rows]
        s.geometry = bytes(self.saveGeometry().toHex()).decode()
        self.store.save_settings()

    def closeEvent(self, e) -> None:
        self._save_settings()
        super().closeEvent(e)


def _setup_logging() -> None:
    folder = data_dir() / "logs"
    folder.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(folder / "miracle.log", maxBytes=512_000, backupCount=2, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[handler])


def main() -> int:
    _setup_logging()
    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("YGH.SanaeMiracle")
        except (AttributeError, OSError):
            pass
    app = QApplication(sys.argv)
    app.setApplicationName(TITLE)
    app.setWindowIcon(app_icon())
    store = Store()
    win = MainWindow(store)
    win.show()
    log.info("%s v%s 시작", TITLE, __version__)
    return app.exec()
