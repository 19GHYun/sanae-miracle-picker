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

from . import __version__, core, sound
from .cutin import MiracleCutIn
from .dice import DiceStage
from .ladder import LadderStage, is_blank
from .lineup import OrderStage, TeamsStage
from .raffle import RaffleStage
from .sanae import IDLE_LINES, SPIN_LINES, SanaeWidget, Sprites
from .store import Draw, Store, data_dir, now_text
from .stream import BACKGROUNDS, BG_COLORS, HOTKEYS, Hotkey, StreamWindow, obs_dir, write_obs
from .wheel import WheelWidget

log = logging.getLogger("Miracle")
TITLE = "사나에의 기적 추첨기"
SPEED = float(os.environ.get("MIRACLE_SPEED") or 1.0)
WHEEL_SECONDS = 5.5
MODES = (("wheel", "🎡 룰렛"), ("raffle", "🎫 당첨자 뽑기"), ("ladder", "🔀 사다리"), ("teams", "👥 팀 나누기"),
         ("order", "🔢 순서 정하기"), ("dice", "🎲 주사위"))
MODE_KEYS = [k for k, _ in MODES]
MODE_ICONS = {"wheel": "🎡", "raffle": "🎫", "ladder": "🔀", "teams": "👥", "order": "🔢", "dice": "🎲"}
TEAM_STYLES = (("number", "1팀 · 2팀 …"), ("touhou", "동방 세력 (하쿠레이 · 모리야 …)"), ("color", "색깔 (빨강 · 파랑 …)"))
DICE_KINDS = (("dice", "주사위"), ("coin", "동전 던지기"), ("number", "숫자 뽑기"))
STYLE = """
QWidget#root { background: #F2FAF4; }
QLabel { font-family: 'Malgun Gothic'; color: #22352A; }
QLabel#hint { color: #6B7F72; font-size: 11px; }
QLabel#result { font-size: 13px; padding: 2px 4px; }
QPushButton { font-family: 'Malgun Gothic'; font-size: 12px; }
QPushButton#mode { background: #FFFFFF; color: #2E6B48; border: 1px solid #B9DEC6; border-radius: 16px;
                   padding: 6px 11px; font-weight: 700; font-size: 13px; }
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
        self.ladder = LadderStage(self)
        self.teams = TeamsStage(self)
        self.order = OrderStage(self)
        self.dice = DiceStage(self)
        self.boards = {"wheel": self.wheel, "raffle": self.raffle, "ladder": self.ladder, "teams": self.teams,
                       "order": self.order, "dice": self.dice}
        self.sanae = SanaeWidget(self)
        self.cutin = MiracleCutIn(self)
        self.mode = "wheel"
        self.bg = "sky"                   # 하늘 / 크로마키 (magenta · blue · green)

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        for key, board in self.boards.items():
            board.setVisible(key == mode)
        self._layout()

    def resizeEvent(self, _e) -> None:
        self._layout()

    def set_bg(self, bg: str) -> None:
        """하늘 / 크로마키. 크로마키일 땐 반투명 그림자를 빼서 키잉 뒤 얼룩이 안 남게."""
        self.bg = bg
        self.wheel.shadow = self.sanae.shadow = bg not in BG_COLORS
        self.update()
        self.wheel.update()

    def _layout(self) -> None:
        w, h = self.width(), self.height()
        f = max(1.0, min(1.7, h / 560))                          # 무대가 크면(방송 창) 사나에도 크게
        self.sanae.set_scale(f)
        left = round(self.LEFT * f)
        area = QRect(left, 6, max(200, w - left - 10), h - 12)
        for board in self.boards.values():
            board.setGeometry(area)
        self.sanae.move(round(-30 * f), h - self.sanae.height() + 2)
        self.sanae.raise_()
        if self.cutin.isVisible():
            self.cutin.setGeometry(self.rect())
            self.cutin.raise_()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        if self.bg in BG_COLORS:                                 # 크로마키: 한 가지 색으로만
            p.fillRect(self.rect(), QColor(BG_COLORS[self.bg]))
            p.end()
            return
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
        left.addLayout(bar)
        self.stage = Stage(root)
        left.addWidget(self.stage, 1)
        self.left = left
        self.stream_win: StreamWindow | None = None
        self.stage_placeholder = QLabel("📺 방송 창에서 무대를 보여 주는 중이에요\n방송 창을 닫으면 여기로 돌아와요",
                                        objectName="hint")
        self.stage_placeholder.setAlignment(Qt.AlignCenter)
        self.stage_placeholder.hide()
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
        self.tabs.addTab(self._stream_tab(), "📺 방송")
        h.addWidget(self.tabs)
        for keys in (Qt.Key_Space, "Ctrl+Return", "F5"):
            QShortcut(QKeySequence(keys), self, activated=self.act)
        self._save_timer = QTimer(self, singleShot=True, interval=600, timeout=self._save_settings)
        self.resize(1100, 740)
        if s.geometry:
            self.restoreGeometry(QByteArray.fromHex(s.geometry.encode()))
        sound.enabled, sound.level = s.sound_on, max(0, min(2, s.sound_level))
        self.stage.set_bg(s.background if s.background in dict(BACKGROUNDS) else "sky")
        self.stage.raffle.on_roll = lambda secs: sound.play("drumroll", secs)
        self.stage.teams.on_step = self.stage.order.on_step = lambda _i: sound.play("pop")
        self.hotkey = Hotkey(self.act)
        self._set_hotkey(s.hotkey if s.hotkey in dict(HOTKEYS) else "off")
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
        self.opts.addWidget(self._ladder_opts())
        self.opts.addWidget(self._teams_opts())
        self.opts.addWidget(self._hint_opts("목록을 섞어서 1번부터 한 명씩 불러 줘요.\n발표 순서 · 게임 차례 · 청소 당번 정하기에."))
        self.opts.addWidget(self._dice_opts())
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

    def _hint_opts(self, text: str) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 6, 0, 0)
        lab = QLabel(text, objectName="hint")
        lab.setWordWrap(True)
        v.addWidget(lab)
        v.addStretch(1)
        return w

    def _ladder_opts(self) -> QWidget:
        s = self.store.settings
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 6, 0, 0)
        v.setSpacing(5)
        v.addWidget(QLabel("<b>아래 칸 결과</b>  (한 줄에 하나 · 모자라면 '꽝')"))
        self.ladder_text = QPlainTextEdit()
        self.ladder_text.setPlainText(s.ladder_results)
        self.ladder_text.setPlaceholderText("당첨\n커피 쏘기\n(비워 두면 당첨 하나 + 나머지 꽝)")
        self.ladder_text.setFixedHeight(96)
        self.ladder_text.textChanged.connect(self._options_changed)
        v.addWidget(self.ladder_text)
        tip = QLabel(f"참가자는 목록에서 (2~{core.LADDER_MAX}명). 진행 중에 버튼을 누르면 남은 사람을 한꺼번에 공개해요.",
                     objectName="hint")
        tip.setWordWrap(True)
        v.addWidget(tip)
        return w

    def _teams_opts(self) -> QWidget:
        s = self.store.settings
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 6, 0, 0)
        v.setSpacing(5)
        row = QHBoxLayout()
        row.addWidget(QLabel("<b>팀 수</b>"))
        self.teams_count = QSpinBox()
        self.teams_count.setRange(2, 12)
        self.teams_count.setValue(max(2, min(12, s.teams_count)))
        self.teams_count.setSuffix(" 팀")
        self.teams_count.valueChanged.connect(self._options_changed)
        row.addWidget(self.teams_count)
        row.addStretch(1)
        v.addLayout(row)
        self.teams_style = QComboBox()
        for key, label in TEAM_STYLES:
            self.teams_style.addItem(label, key)
        self.teams_style.setCurrentIndex(max(0, [k for k, _ in TEAM_STYLES].index(s.teams_style)
                                             if s.teams_style in dict(TEAM_STYLES) else 0))
        self.teams_style.currentIndexChanged.connect(self._options_changed)
        v.addWidget(self.teams_style)
        tip = QLabel("섞어서 차례로 나눠 줘서 팀 인원 차이는 많아야 1명이에요.", objectName="hint")
        tip.setWordWrap(True)
        v.addWidget(tip)
        return w

    def _dice_opts(self) -> QWidget:
        s = self.store.settings
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 6, 0, 0)
        v.setSpacing(5)
        self.dice_kind = QComboBox()
        for key, label in DICE_KINDS:
            self.dice_kind.addItem(label, key)
        self.dice_kind.setCurrentIndex([k for k, _ in DICE_KINDS].index(s.dice_kind) if s.dice_kind in dict(DICE_KINDS) else 0)
        self.dice_kind.currentIndexChanged.connect(self._options_changed)
        v.addWidget(self.dice_kind)
        row = QHBoxLayout()
        row.addWidget(QLabel("개수"))
        self.dice_count = QSpinBox()
        self.dice_count.setRange(1, 10)
        self.dice_count.setValue(max(1, min(10, s.dice_count)))
        self.dice_count.valueChanged.connect(self._options_changed)
        row.addWidget(self.dice_count)
        self.dice_sides_label = QLabel("면")
        row.addWidget(self.dice_sides_label)
        self.dice_sides = QComboBox()
        for n in core.DICE_SIDES:
            self.dice_sides.addItem(f"d{n}", n)
        self.dice_sides.setCurrentIndex(core.DICE_SIDES.index(s.dice_sides) if s.dice_sides in core.DICE_SIDES else 1)
        self.dice_sides.currentIndexChanged.connect(self._options_changed)
        row.addWidget(self.dice_sides)
        row.addStretch(1)
        v.addLayout(row)
        self.num_row = QWidget()
        nr = QHBoxLayout(self.num_row)
        nr.setContentsMargins(0, 0, 0, 0)
        self.num_lo, self.num_hi = QSpinBox(), QSpinBox()
        for box, val in ((self.num_lo, s.num_lo), (self.num_hi, s.num_hi)):
            box.setRange(-999999, 999999)
            box.setValue(val)
            box.valueChanged.connect(self._options_changed)
        nr.addWidget(self.num_lo)
        nr.addWidget(QLabel("~"))
        nr.addWidget(self.num_hi)
        nr.addStretch(1)
        v.addWidget(self.num_row)
        self.num_unique = QCheckBox("같은 숫자는 한 번만")
        self.num_unique.setChecked(s.num_unique)
        self.num_unique.toggled.connect(self._options_changed)
        v.addWidget(self.num_unique)
        tip = QLabel("주사위 모드는 목록을 쓰지 않아요.", objectName="hint")
        v.addWidget(tip)
        return w

    def _dice_spec(self) -> tuple[str, int, int, int, int, bool]:
        return (self.dice_kind.currentData(), self.dice_count.value(), self.dice_sides.currentData(),
                self.num_lo.value(), self.num_hi.value(), self.num_unique.isChecked())

    def _options_changed(self, *_a) -> None:
        kind = self.dice_kind.currentData()
        self.dice_sides.setVisible(kind == "dice")
        self.dice_sides_label.setVisible(kind == "dice")
        self.num_row.setVisible(kind == "number")
        self.num_unique.setVisible(kind == "number")
        self._preview()
        self._queue_save()

    def _preview(self) -> None:
        """추첨 전 무대 미리보기 (사다리 이름·결과 칸, 팀 카드, 주사위 개수)."""
        names = core.names_of(core.parse(self.editor.toPlainText()))
        if self.mode == "ladder":
            names = names[:core.LADDER_MAX]
            self.stage.ladder.preview(names, core.ladder_results(self.ladder_text.toPlainText(), len(names)))
        elif self.mode == "teams":
            n = self.teams_count.value()
            self.stage.teams.preview(n, core.team_names(n, self.teams_style.currentData()))
        elif self.mode == "dice":
            kind, count, sides, lo, hi, _u = self._dice_spec()
            self.stage.dice.preview(kind, count, sides, lo, hi)

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
            icon = MODE_ICONS.get(d.mode, "✨")
            item = QListWidgetItem(f"{d.when[5:16].replace('T', ' ')}  {icon} {d.title}  ({d.count}개)\n"
                                   f"→ {core.summary(d.mode, d.result)}\n   시드 {core.seed_text(d.seed)} · 지문 {d.print_}")
            item.setData(Qt.UserRole, d)
            self.hist.addItem(item)

    def draw_text(self, d: Draw) -> str:
        kind = core.MODE_NAMES.get(d.mode, d.mode)
        lines = [f"[{TITLE}] {d.when.replace('T', ' ')}",
                 f"{kind} · {d.title}" if d.mode == "dice" else f"{kind} · 목록: {d.title} ({d.count}개)"]
        if d.mode == "wheel":
            lines.append(f"결과: {d.result[0]}")
        elif d.mode == "order":
            lines += [f"{i + 1}. {n}" for i, n in enumerate(d.result)]
        elif d.mode == "ladder":
            lines += [f"{a} → {b}" for a, b in d.result]
        elif d.mode == "dice":
            lines.append(core.summary("dice", d.result))
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
        self._preview()
        self._queue_save()

    # ── 모드 ──
    def set_mode(self, mode: str) -> None:
        if self.busy:
            self.mode_btns[self.mode].setChecked(True)
            return
        self.mode = mode
        self.mode_btns[mode].setChecked(True)
        self.stage.set_mode(mode)
        self.opts.setCurrentIndex(MODE_KEYS.index(mode))
        self.editor.setEnabled(mode != "dice")                  # 주사위는 목록을 안 씀
        self._options_changed()
        self._update_go()
        self._queue_save()

    @property
    def busy(self) -> bool:
        r, st = self.stage.raffle, self.stage
        return (st.wheel.spinning or r.phase == "rolling" or r.waiting
                or any(b.busy for b in (st.ladder, st.teams, st.order, st.dice)))

    def _update_go(self) -> None:
        r, st = self.stage.raffle, self.stage
        if any(b.busy for b in (st.ladder, st.teams, st.order, st.dice)):
            self.go.setText("⏩ 바로 결과 보기")
            self.go.setEnabled(True)
        elif st.wheel.spinning or r.phase == "rolling":
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
        for board in (self.stage.ladder, self.stage.teams, self.stage.order, self.stage.dice):
            if board.busy:                                       # 진행 중 → 바로 결과
                board.skip()
                self._update_go()
                return
        if self.busy:
            return
        entries = core.parse(self.editor.toPlainText())
        {"wheel": self._spin, "raffle": self._draw, "ladder": self._ladder, "teams": self._teams,
         "order": self._order, "dice": lambda _e: self._dice()}[self.mode](entries)

    def _title(self) -> str:
        name = self.list_box.currentText()
        if name and self.store.lists.get(name, "").strip() == self.editor.toPlainText().strip():
            return name
        return f"{name} (고침)" if name else "저장 안 한 목록"

    def _spin(self, entries: list[core.Entry]) -> None:
        if not entries:
            self._oops("목록이 비어 있어요! 오른쪽에 적어 주세요.")
            return
        seed = core.new_seed()
        idx, frac = core.spin(entries, seed)
        self.stage.wheel.set_entries(entries)
        self.stage.sanae.set_mode("spin", random.choice(SPIN_LINES), 2.5)
        self.stage.wheel.spin_to(idx, frac, WHEEL_SECONDS * SPEED, lambda i: self._spun(entries, i, seed))
        sound.play("spin", WHEEL_SECONDS * SPEED, self.stage.wheel.ticks)
        self._update_go()
        log.info("룰렛: %d개, 시드 %s", len(entries), core.seed_text(seed))

    def _spun(self, entries: list[core.Entry], idx: int, seed: int) -> None:
        name = entries[idx].name
        text = self.editor.toPlainText()
        d = Draw(now_text(), "wheel", self._title(), len(entries), seed, core.fingerprint(entries), [name], text)
        self.store.add(d)
        self._refresh_history()
        self.stage.sanae.set_mode("happy", f"「{name}」! 기적이에요!", 5.5)
        self._miracle("✨ 기적 발생! ✨", name)
        self._obs("wheel", [name])
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
            self._oops("목록이나 등수가 비어 있어요!" if not entries else "등수의 인원을 정해 주세요!")
            return
        exclude = self._last_winners() if self.exclude_last.isChecked() else set()
        seed = core.new_seed()
        results = core.raffle(entries, tiers, seed, self.unique.isChecked(), exclude)
        order = core.reveal_order(results)
        if not order:
            self._oops("뽑을 수 있는 사람이 없어요…")
            return
        self._pending = (entries, results, seed, self.editor.toPlainText())
        self.stage.sanae.set_mode("spin", "누가 뽑힐까요…!", 2.0)
        self.stage.raffle.start(results, order, [e.name for e in entries], self._revealed, self._raffle_done,
                                auto=self.auto.isChecked(), speed=SPEED)
        self._update_go()
        log.info("당첨자 뽑기: %d명, 등수 %s, 시드 %s", len(entries), [(t.name, t.count) for t in tiers], core.seed_text(seed))

    def _revealed(self, tier: str, name: str, n: int, total: int) -> None:
        if n == total:
            self._miracle(f"✨ {tier} — 기적 발생! ✨", name)
            self.stage.sanae.set_mode("happy", f"{tier}은(는) 「{name}」! 축하해요!", 4.0)
        else:
            self.stage.sanae.set_mode("happy", f"{tier}: 「{name}」!", 2.5)
            sound.play("win")
        self._update_go()

    def _raffle_done(self) -> None:
        entries, results, seed, text = self._pending
        d = Draw(now_text(), "raffle", self._title(), len(entries), seed, core.fingerprint(entries), results, text)
        self.store.add(d)
        self._refresh_history()
        self._obs("raffle", results)
        self.result.setText(f"🎫 {core.summary('raffle', results)}   ·   {len(entries)}명 중   ·   시드 {core.seed_text(seed)}")
        QTimer.singleShot(0, self._update_go)
        log.info("당첨자 뽑기 결과: %s", core.summary("raffle", results))

    def _record(self, mode: str, title: str, count: int, seed: int, entries: list[core.Entry], result, text: str) -> None:
        self.store.add(Draw(now_text(), mode, title, count, seed, core.fingerprint(entries), result, text))
        self._refresh_history()
        self._obs(mode, result)
        self.result.setText(f"{MODE_ICONS[mode]} {core.summary(mode, result)}   ·   시드 {core.seed_text(seed)}")
        QTimer.singleShot(0, self._update_go)
        log.info("%s 결과: %s", core.MODE_NAMES[mode], core.summary(mode, result))

    # ── 사다리 ──
    def _ladder(self, entries: list[core.Entry]) -> None:
        names = core.names_of(entries)
        if not 2 <= len(names) <= core.LADDER_MAX:
            self._oops(f"사다리는 2~{core.LADDER_MAX}명이 탈 수 있어요!")
            return
        bottom = core.ladder_results(self.ladder_text.toPlainText(), len(names))
        seed = core.new_seed()
        lad = core.ladder(len(names), seed)
        self._pending = (entries, seed, self.editor.toPlainText(), names, bottom, lad)
        self.stage.sanae.set_mode("spin", "어디로 내려갈까요~?", 2.0)
        self.stage.ladder.start(names, bottom, lad, self._ladder_step, self._ladder_done, SPEED)
        self._update_go()

    def _ladder_step(self, name: str, result: str) -> None:
        if is_blank(result):
            self.stage.sanae.say(f"{name}: {result}", 1.6)
            sound.play("pop")
        else:
            self.stage.sanae.set_mode("happy", f"「{name}」 → {result}!", 2.5)
            sound.play("win")

    def _ladder_done(self) -> None:
        entries, seed, text, names, bottom, lad = self._pending
        pairs = [[names[s], bottom[lad.end_of(s)]] for s in range(len(names))]
        hits = [(a, b) for a, b in pairs if not is_blank(b)]
        if len(hits) == 1:
            self._miracle("✨ 사다리 결과 ✨", f"{hits[0][0]} → {hits[0][1]}")
        else:
            self._miracle("✨ 사다리 완료 ✨", "모두 공개!")
        self._record("ladder", self._title(), len(names), seed, entries, pairs, text)

    # ── 팀 나누기 ──
    def _teams(self, entries: list[core.Entry]) -> None:
        names = core.names_of(entries)
        if len(names) < 2:
            self._oops("두 명 이상 적어 주세요!")
            return
        n = min(self.teams_count.value(), len(names))
        seed = core.new_seed()
        result = core.teams(entries, n, seed, self.teams_style.currentData())
        self._pending = (entries, seed, self.editor.toPlainText(), result)
        self.stage.sanae.set_mode("spin", "팀을 나눠 볼게요!", 2.0)
        self.stage.teams.start(result, self._teams_done, SPEED)
        self._update_go()

    def _teams_done(self) -> None:
        entries, seed, text, result = self._pending
        self.stage.sanae.set_mode("happy", "팀이 정해졌어요! 다들 힘내요~", 4.0)
        self._miracle("✨ 팀 나누기 완료 ✨", f"{len(result)}팀 · {len(entries)}명")
        self._record("teams", self._title(), len(entries), seed, entries, [[t, list(m)] for t, m in result], text)

    # ── 순서 정하기 ──
    def _order(self, entries: list[core.Entry]) -> None:
        if len(entries) < 2:
            self._oops("두 명 이상 적어 주세요!")
            return
        seed = core.new_seed()
        result = core.order(entries, seed)
        self._pending = (entries, seed, self.editor.toPlainText(), result)
        self.stage.sanae.set_mode("spin", "순서를 정해 볼게요!", 2.0)
        self.stage.order.start(result, self._order_done, SPEED)
        self._update_go()

    def _order_done(self) -> None:
        entries, seed, text, result = self._pending
        self.stage.sanae.set_mode("happy", f"1번은 「{result[0]}」!", 4.0)
        self._miracle("✨ 1번은… ✨", result[0])
        self._record("order", self._title(), len(entries), seed, entries, result, text)

    # ── 주사위 · 동전 · 숫자 ──
    def _dice(self) -> None:
        kind, count, sides, lo, hi, unique = self._dice_spec()
        seed = core.new_seed()
        values = core.roll(kind, seed, count, sides, lo, hi, unique)
        label = core.dice_label(kind, len(values), sides, lo, hi)
        self._pending = (seed, label, values, kind)
        self.stage.sanae.set_mode("spin", {"coin": "던져 볼게요~!", "number": "숫자를 뽑아 볼게요!"}.get(kind, "굴려 볼게요~!"), 2.0)
        self.stage.dice.start(kind, values, sides, lo, hi, self._dice_done, SPEED)
        sound.play("rattle", 1.6 * SPEED)
        self._update_go()

    def _dice_done(self) -> None:
        seed, label, values, kind = self._pending
        if kind == "dice" and len(values) > 1:
            big = f"합계 {sum(values)}"
        elif kind == "coin" and len(values) == 1:
            big = f"{values[0]}면!"
        else:
            big = ", ".join(str(v) for v in values)
        self.stage.sanae.set_mode("happy", f"{big}! 기적이에요~", 4.0)
        self._miracle(f"✨ {label} ✨", big, burst=60, sound_name="coin" if kind == "coin" else "fanfare")
        self._record("dice", label, len(values), seed, [], [label, values], "")

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
        s.ladder_results = self.ladder_text.toPlainText()
        s.teams_count = self.teams_count.value()
        s.teams_style = self.teams_style.currentData()
        s.dice_kind, s.dice_count, s.dice_sides, s.num_lo, s.num_hi, s.num_unique = self._dice_spec()
        s.geometry = bytes(self.saveGeometry().toHex()).decode()
        s.sound_on = self.sound_on.isChecked()
        s.sound_level = self.sound_level.currentIndex()
        s.background = self.bg_box.currentData()
        s.hotkey = self.hotkey_box.currentData()
        s.obs_text = self.obs_on.isChecked()
        self.store.save_settings()

    def closeEvent(self, e) -> None:
        self._save_settings()
        if self.stream_win is not None:
            self.stream_win.close()
        self.hotkey.clear()
        sound.stop()
        super().closeEvent(e)

    # ── 연출 · 효과음 ──
    def _miracle(self, title: str, text: str, burst: int = 90, sound_name: str = "fanfare") -> None:
        sound.play(sound_name)
        self.stage.cutin.play(title, text, SPEED, burst=burst, hide=self.stage.sanae)

    def _oops(self, text: str) -> None:
        self.stage.sanae.set_mode("oops", text, 3.0)
        sound.play("boop")

    # ── 방송 ──
    def _stream_tab(self) -> QWidget:
        s = self.store.settings
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(6)

        def hint(text: str) -> None:
            lab = QLabel(text, objectName="hint")
            lab.setWordWrap(True)
            v.addWidget(lab)
        v.addWidget(QLabel("<b>🔊 효과음</b>"))
        row = QHBoxLayout()
        self.sound_on = QCheckBox("효과음 내기")
        self.sound_on.setChecked(s.sound_on)
        self.sound_on.toggled.connect(self._sound_changed)
        self.sound_level = QComboBox()
        self.sound_level.addItems(["작게", "보통", "크게"])
        self.sound_level.setCurrentIndex(max(0, min(2, s.sound_level)))
        self.sound_level.currentIndexChanged.connect(self._sound_changed)
        listen = QPushButton("▶ 들어보기", objectName="small")
        listen.setCursor(Qt.PointingHandCursor)
        listen.clicked.connect(lambda: sound.play("fanfare"))
        row.addWidget(self.sound_on)
        row.addWidget(self.sound_level)
        row.addWidget(listen)
        row.addStretch(1)
        v.addLayout(row)
        v.addSpacing(6)
        v.addWidget(QLabel("<b>🎨 무대 배경</b>"))
        self.bg_box = QComboBox()
        for key, label in BACKGROUNDS:
            self.bg_box.addItem(label, key)
        self.bg_box.setCurrentIndex([k for k, _ in BACKGROUNDS].index(s.background) if s.background in dict(BACKGROUNDS) else 0)
        self.bg_box.currentIndexChanged.connect(self._bg_changed)
        v.addWidget(self.bg_box)
        hint("OBS 의 크로마 키 필터로 배경을 지울 수 있어요. 사나에 머리가 초록이라 자홍·파랑을 추천해요.")
        v.addSpacing(6)
        v.addWidget(QLabel("<b>📺 방송 창</b>"))
        self.stream_btn = QPushButton("📺 무대만 따로 띄우기", objectName="small")
        self.stream_btn.setCursor(Qt.PointingHandCursor)
        self.stream_btn.clicked.connect(self.toggle_stream)
        v.addWidget(self.stream_btn, 0, Qt.AlignLeft)
        hint("무대만 큰 창으로 띄워요 (OBS 창 캡처용). 조작은 이 창에서 하고, 방송 창에서도 Space 로 진행돼요.")
        v.addSpacing(6)
        v.addWidget(QLabel("<b>⌨ 전역 단축키</b>  (다른 창을 보고 있어도)"))
        row2 = QHBoxLayout()
        self.hotkey_box = QComboBox()
        for key, label in HOTKEYS:
            self.hotkey_box.addItem(label, key)
        self.hotkey_box.setCurrentIndex([k for k, _ in HOTKEYS].index(s.hotkey) if s.hotkey in dict(HOTKEYS) else 0)
        self.hotkey_box.currentIndexChanged.connect(lambda _i: self._set_hotkey(self.hotkey_box.currentData()))
        self.hotkey_state = QLabel(objectName="hint")
        row2.addWidget(self.hotkey_box)
        row2.addWidget(self.hotkey_state, 1)
        v.addLayout(row2)
        hint("게임·방송 프로그램을 보고 있을 때도 이 키로 바로 기적을 일으켜요. 누른 키는 기록하지 않아요.")
        v.addSpacing(6)
        v.addWidget(QLabel("<b>📝 OBS 텍스트</b>"))
        self.obs_on = QCheckBox("결과를 텍스트 파일로 내보내기")
        self.obs_on.setChecked(s.obs_text)
        self.obs_on.toggled.connect(self._queue_save)
        v.addWidget(self.obs_on)
        path = QLabel("%APPDATA%\\SanaeMiracle\\obs  (winner.txt · result.txt)", objectName="hint")
        path.setToolTip(str(obs_dir()))
        path.setWordWrap(True)
        path.setTextInteractionFlags(Qt.TextSelectableByMouse)
        v.addWidget(path)
        open_btn = QPushButton("📁 폴더 열기", objectName="small")
        open_btn.setCursor(Qt.PointingHandCursor)
        open_btn.clicked.connect(self._open_obs_dir)
        v.addWidget(open_btn, 0, Qt.AlignLeft)
        hint("OBS 텍스트 소스 → '파일에서 읽기' 로 winner.txt(한 줄 결과) 또는 result.txt(자세히)를 고르세요. "
             "추첨이 끝날 때마다 바뀌어요.")
        v.addStretch(1)
        return w

    def _sound_changed(self, *_a) -> None:
        sound.enabled = self.sound_on.isChecked()
        sound.level = self.sound_level.currentIndex()
        self._queue_save()

    def _bg_changed(self, *_a) -> None:
        self.stage.set_bg(self.bg_box.currentData())
        self._queue_save()

    def _set_hotkey(self, key: str) -> None:
        ok = self.hotkey.set(key)
        self.hotkey_state.setText("" if key == "off" else ("✔ 등록됐어요" if ok else "✖ 다른 프로그램이 이미 쓰고 있어요"))
        self._queue_save()

    def toggle_stream(self) -> None:
        if self.stream_win is not None:
            self.stream_win.close()
            return
        self.stream_win = StreamWindow(self._stream_closed, self.act)
        idx = self.left.indexOf(self.stage)
        self.left.removeWidget(self.stage)
        self.left.insertWidget(idx, self.stage_placeholder, 1)
        self.stage_placeholder.show()
        self.stream_win.box.addWidget(self.stage)
        self.stage.show()
        self.stream_win.setWindowIcon(app_icon())
        self.stream_win.show()
        self.stream_btn.setText("↩ 무대 되돌리기")
        log.info("방송 창 열기")

    def _stream_closed(self) -> None:
        self.stream_win = None
        idx = self.left.indexOf(self.stage_placeholder)
        self.left.removeWidget(self.stage_placeholder)
        self.stage_placeholder.hide()
        self.left.insertWidget(idx, self.stage, 1)
        self.stage.show()
        self.stream_btn.setText("📺 무대만 따로 띄우기")
        log.info("방송 창 닫기")

    def _obs(self, mode: str, result) -> None:
        if not self.obs_on.isChecked() or not self.store.history:
            return
        try:
            write_obs(core.headline(mode, result), self.draw_text(self.store.history[0]))
        except OSError:
            log.warning("OBS 텍스트 쓰기 실패", exc_info=True)

    def _open_obs_dir(self) -> None:
        d = obs_dir()
        d.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(str(d))


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
