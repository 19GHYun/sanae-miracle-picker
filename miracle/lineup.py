# -*- coding: utf-8 -*-
"""팀 나누기 · 순서 정하기 무대: 한 명씩 차례로 나눠 주거나(팀 카드), 1번부터 불러 준다(순서 목록)."""
from __future__ import annotations

import math
import time
from typing import Callable

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget
from .i18n import T, font

TEAM_COLORS = ["#E8657A", "#3D7DD8", "#2E9E5B", "#F2A230", "#8E6CD8", "#3FB7C4", "#D8579A", "#7FBF3F",
               "#F28C38", "#5B8DEF", "#C9A030", "#4FA3A0"]
NAMED_COLORS = {"빨강": "#E04848", "파랑": "#3D6FD8", "초록": "#2E9E5B", "노랑": "#E0B020", "보라": "#8E5CD8",
                "주황": "#F08030", "하늘": "#3FB7E4", "분홍": "#E870A8", "하양": "#B8B8B8", "검정": "#3A3A3A",
                "회색": "#8A8A8A", "갈색": "#8E5B36"}


def team_color(name: str, i: int) -> QColor:
    """'빨강 팀' 같은 색깔 팀은 그 색으로 (번역된 이름이어도)."""
    for color, code in NAMED_COLORS.items():
        if name == T("{name} 팀", name=T(color)):
            return QColor(code)
    return QColor(TEAM_COLORS[i % len(TEAM_COLORS)])


def _fit(p: QPainter, text: str, rect: QRectF, size: int, bold: bool = True, minimum: int = 9) -> None:
    f = QFont(font())
    f.setBold(bold)
    f.setPixelSize(size)
    while size > minimum and QFontMetricsF(f).horizontalAdvance(text) > rect.width():
        size -= 1
        f.setPixelSize(size)
    p.setFont(f)
    p.drawText(rect, Qt.AlignLeft | Qt.AlignVCenter, QFontMetricsF(f).elidedText(text, Qt.ElideRight, rect.width()))


def _grid(n: int, body: QRectF, line_max: float, line_min: float, max_cols: int) -> tuple[int, int, float, int]:
    """n 줄을 body 에 열로 나눠 놓기: (한 열의 줄 수, 열 수, 줄 높이, 들어가는 줄 수 — 모자라면 n 보다 작음)."""
    per_col = max(1, int(body.height() // line_max))
    ncol = min(max_cols, max(1, math.ceil(n / per_col)))
    per_col = max(per_col, math.ceil(n / ncol))                    # 열을 다 쓰면 줄을 촘촘하게
    per_col = min(per_col, max(1, int(body.height() // line_min)))  # 그래도 글자가 안 보일 만큼은 아니게
    return per_col, ncol, min(line_max, body.height() / per_col), min(n, per_col * ncol)


def _tail(items: list[str], room: int) -> list[tuple[int, str]]:
    """[(번호, 글)] — 다 안 들어가면 앞쪽은 "… 앞의 N명" 한 줄(번호 -1)로 줄이고 최근 것만."""
    if len(items) <= room:
        return list(enumerate(items))
    keep = max(0, room - 1)
    start = len(items) - keep
    return [(-1, T("… 앞의 {n}명", n=start))] + [(start + k, x) for k, x in enumerate(items[start:])]


class _Reveal(QWidget):
    """한 명씩 차례로 보여 주는 무대의 공통 부분."""

    STEP = 0.3
    MAX_TOTAL = 9.0       # 사람이 많으면 한 명당 시간을 줄여서 이 안에

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.shown = 0
        self.total = 0
        self.phase = "idle"
        self.speed = 1.0
        self._step = self.STEP
        self._t0 = 0.0
        self._on_done: Callable[[], None] | None = None
        self.on_step: Callable[[int], None] | None = None     # 한 명 더 나올 때 — 뿅
        self.timer = QTimer(self, timeout=self._tick, interval=30)

    @property
    def busy(self) -> bool:
        return self.phase == "running"

    def _begin(self, total: int, on_done: Callable[[], None], speed: float) -> None:
        self.total, self.shown, self.speed, self._on_done = total, 0, speed, on_done
        self._step = min(self.STEP, self.MAX_TOTAL / max(1, total))
        self.phase, self._t0 = "running", time.monotonic()
        self.timer.start()

    def skip(self) -> None:
        if self.busy:
            self.shown = self.total
            self._finish()

    def _finish(self) -> None:
        self.phase = "done"
        self.timer.stop()
        self.update()
        if self._on_done:
            self._on_done()

    def _tick(self) -> None:
        before = self.shown
        self.shown = min(self.total, int((time.monotonic() - self._t0) / (self._step * self.speed)) + 1)
        if self.shown > before and self.on_step:
            self.on_step(self.shown)
        if self.shown >= self.total and time.monotonic() - self._t0 > (self.total * self._step + 0.4) * self.speed:
            self._finish()
            return
        self.update()


class TeamsStage(_Reveal):
    STEP = 0.22

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.teams: list[tuple[str, list[str]]] = []
        self.deal: list[tuple[int, str]] = []      # 나눠 주는 순서 (팀 번호, 이름)

    def start(self, teams: list[tuple[str, list[str]]], on_done: Callable[[], None], speed: float = 1.0) -> None:
        self.teams = teams
        n = len(teams)
        longest = max((len(m) for _, m in teams), default=0)
        self.deal = [(t, teams[t][1][i]) for i in range(longest) for t in range(n) if i < len(teams[t][1])]
        self._begin(len(self.deal), on_done, speed)

    def preview(self, n_teams: int, style_names: list[str]) -> None:
        if self.busy:
            return
        self.teams = [(name, []) for name in style_names[:n_teams]]
        self.deal, self.shown, self.phase = [], 0, "idle"
        self.update()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        n = len(self.teams)
        if not n:
            p.end()
            return
        cols = 1 if n == 1 else 2 if n <= 4 else 3 if n <= 9 else 4
        rows = math.ceil(n / cols)
        gap = 12
        w = (self.width() - 24 - gap * (cols - 1)) / cols
        h = (self.height() - 24 - gap * (rows - 1)) / rows
        members: list[list[str]] = [[] for _ in range(n)]
        for t, name in self.deal[:self.shown]:
            members[t].append(name)
        newest = self.deal[self.shown - 1] if self.busy and self.shown else None
        for i, (name, _) in enumerate(self.teams):
            r = QRectF(12 + (i % cols) * (w + gap), 12 + (i // cols) * (h + gap), w, h)
            col = team_color(name, i)
            path = QPainterPath()
            path.addRoundedRect(r, 14, 14)
            p.setPen(QPen(col, 2.5))
            p.setBrush(QColor(255, 255, 255, 228))
            p.drawPath(path)
            head = QRectF(r.left(), r.top(), r.width(), 36)
            p.save()
            p.setClipPath(path)
            p.fillRect(head, col)
            p.restore()
            p.setPen(QColor("#FFFFFF"))
            _fit(p, T("  {name}   ({v3}명)", name=name, v3=len(members[i])), head.adjusted(6, 0, -6, 0), 15)
            names = members[i]
            if not names:
                continue
            body = r.adjusted(14, 44, -10, -8)
            per_col, ncol, line_h, room = _grid(len(names), body, 24.0, 14.0, max(1, int(body.width() // 70)))
            cw = body.width() / ncol
            for k, (j, who) in enumerate(_tail(names, room)):
                cell = QRectF(body.left() + (k // per_col) * cw, body.top() + (k % per_col) * line_h, cw - 6, line_h)
                if j < 0:
                    p.setPen(QColor("#7A8B80"))
                    _fit(p, who, cell, 13, bold=False)
                    continue
                hot = newest is not None and newest == (i, who) and j == len(names) - 1
                p.setPen(QColor("#C8102E") if hot else QColor("#22352A"))
                _fit(p, f"· {who}", cell, 15 if hot else 14, bold=hot)
        p.end()


class OrderStage(_Reveal):
    STEP = 0.45

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.names: list[str] = []

    def start(self, names: list[str], on_done: Callable[[], None], speed: float = 1.0) -> None:
        self.names = names
        self._begin(len(names), on_done, speed)

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        top = QRectF(24, 20, w - 48, min(120.0, h * 0.26))
        path = QPainterPath()
        path.addRoundedRect(top, 18, 18)
        p.setPen(QPen(QColor("#2E9E5B"), 3))
        p.setBrush(QColor("#FFFFFF"))
        p.drawPath(path)
        if self.shown:
            k = self.shown
            big = QFont(font())
            big.setBold(True)
            big.setPixelSize(22)
            p.setFont(big)
            p.setPen(QColor("#2E9E5B"))
            p.drawText(top.adjusted(22, 0, 0, 0), Qt.AlignLeft | Qt.AlignVCenter, T("{k}번", k=k))
            p.setPen(QColor("#C8102E") if k == 1 else QColor("#22352A"))
            _fit(p, self.names[k - 1], top.adjusted(110, 0, -20, 0), 40)
        else:
            f = QFont(font(), 14)
            f.setBold(True)
            p.setFont(f)
            p.setPen(QColor("#7A8B80"))
            p.drawText(top, Qt.AlignCenter, T("✨ 기적을 일으키면 1번부터 불러 줄게요"))
        body = QRectF(24, top.bottom() + 16, w - 48, h - top.bottom() - 28)
        shown = self.names[:self.shown]
        if not shown:
            p.end()
            return
        per_col, ncol, line_h, room = _grid(len(self.names), body, 28.0, 13.0, 4)
        cw = body.width() / ncol
        for k, (i, who) in enumerate(_tail(shown, room)):
            cell = QRectF(body.left() + (k // per_col) * cw, body.top() + (k % per_col) * line_h, cw - 10, line_h)
            if i < 0:
                p.setPen(QColor("#7A8B80"))
                _fit(p, who, cell, 13, bold=False)
                continue
            p.setPen(QColor("#2E9E5B"))
            _fit(p, f"{i + 1:>2}.", QRectF(cell.left(), cell.top(), 34, line_h), 14)
            p.setPen(QColor("#C8102E") if i == 0 else QColor("#22352A"))
            _fit(p, who, cell.adjusted(36, 0, 0, 0), 14, bold=i == self.shown - 1)
        p.end()
