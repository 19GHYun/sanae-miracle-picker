# -*- coding: utf-8 -*-
"""사다리타기 무대: 위에 참가자, 아래에 결과(처음엔 ?), 가로줄이 깔린 뒤 한 명씩 색깔 선으로 따라 내려간다."""
from __future__ import annotations

import math
import time
from typing import Callable

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from .core import Ladder, is_blank
from .i18n import T, font

COLORS = ["#E8657A", "#3D7DD8", "#2E9E5B", "#F2A230", "#8E6CD8", "#3FB7C4", "#D8579A", "#7FBF3F",
          "#F28C38", "#5B8DEF", "#C9A030", "#4FA3A0"]
DRAW_TIME = 0.9       # 가로줄이 깔리는 시간
TRACE_TIME = 1.3      # 한 명이 내려가는 시간
GAP_TIME = 0.35


class LadderStage(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.top: list[str] = []
        self.bottom: list[str] = []
        self.ladder: Ladder | None = None
        self.phase = "idle"                    # idle / drawing / tracing / done
        self.done_starts: list[int] = []
        self.current: int | None = None
        self.progress = 0.0
        self.speed = 1.0
        self._t0 = 0.0
        self._on_each: Callable[[str, str], None] | None = None
        self._on_done: Callable[[], None] | None = None
        self.timer = QTimer(self, timeout=self._tick, interval=16)

    @property
    def busy(self) -> bool:
        return self.phase in ("drawing", "tracing")

    def preview(self, top: list[str], bottom: list[str]) -> None:
        """추첨 전: 이름과 가려진 결과 칸만."""
        if self.busy:
            return
        self.top, self.bottom = top, bottom
        self.ladder, self.phase, self.done_starts, self.current = None, "idle", [], None
        self.update()

    def start(self, top: list[str], bottom: list[str], ladder: Ladder, on_each: Callable[[str, str], None],
              on_done: Callable[[], None], speed: float = 1.0) -> None:
        self.top, self.bottom, self.ladder = top, bottom, ladder
        self._on_each, self._on_done, self.speed = on_each, on_done, speed
        self.done_starts, self.current = [], None
        self.phase, self._t0 = "drawing", time.monotonic()
        self.timer.start()

    def skip(self) -> None:
        """남은 사람을 한꺼번에 공개."""
        if not self.busy or self.ladder is None:
            return
        for s in range(self.ladder.n):
            if s not in self.done_starts:
                self.done_starts.append(s)
                if self._on_each:
                    self._on_each(self.top[s], self.bottom[self.ladder.end_of(s)])
        self._finish()

    def _finish(self) -> None:
        self.current, self.phase = None, "done"
        self.timer.stop()
        self.update()
        if self._on_done:
            self._on_done()

    def _tick(self) -> None:
        t = time.monotonic() - self._t0
        if self.phase == "drawing":
            if t >= DRAW_TIME * self.speed:
                self.phase, self.current, self._t0 = "tracing", 0, time.monotonic()
        elif self.phase == "tracing" and self.current is not None:
            self.progress = min(1.0, t / (TRACE_TIME * self.speed))
            if t >= (TRACE_TIME + GAP_TIME) * self.speed:
                s = self.current
                self.done_starts.append(s)
                if self._on_each:
                    self._on_each(self.top[s], self.bottom[self.ladder.end_of(s)])
                if len(self.done_starts) >= self.ladder.n:
                    self._finish()
                    return
                self.current, self._t0, self.progress = s + 1, time.monotonic(), 0.0
        self.update()

    # ── 모양 ──
    def _geom(self) -> tuple[float, float, float, float]:
        n = max(1, len(self.top))
        left, right = 20.0, self.width() - 20.0
        colw = (right - left) / n
        return left, colw, 64.0, self.height() - 64.0     # 왼쪽, 칸 너비, 사다리 위, 사다리 아래

    def _x(self, col: int) -> float:
        left, colw, _, _ = self._geom()
        return left + (col + 0.5) * colw

    def _y(self, row: int) -> float:
        _, _, top, bottom = self._geom()
        rows = self.ladder.rows if self.ladder else 10
        if row < 0:
            return top
        if row >= rows:
            return bottom
        return top + (row + 1) * (bottom - top) / (rows + 1)

    def path_points(self, start: int) -> list[QPointF]:
        return [QPointF(self._x(c), self._y(r)) for r, c in self.ladder.trace(start)]

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        n = len(self.top)
        if n < 2:
            f = QFont(font(), 13)
            f.setBold(True)
            p.setFont(f)
            p.setPen(QColor("#5A6B60"))
            p.drawText(self.rect(), Qt.AlignCenter, T("사다리는 2명부터 탈 수 있어요\n(오른쪽 목록에 한 줄에 한 명씩)"))
            p.end()
            return
        _, colw, top, bottom = self._geom()
        p.setPen(QPen(QColor("#5B4636"), 4, Qt.SolidLine, Qt.RoundCap))       # 세로줄
        for c in range(n):
            p.drawLine(QPointF(self._x(c), top), QPointF(self._x(c), bottom))
        if self.ladder is not None:                                          # 가로줄
            shown = len(self.ladder.rungs)
            if self.phase == "drawing":
                shown = int(len(self.ladder.rungs) * min(1.0, (time.monotonic() - self._t0) / (DRAW_TIME * self.speed)))
            for r, c in self.ladder.rungs[:shown]:
                p.drawLine(QPointF(self._x(c), self._y(r)), QPointF(self._x(c + 1), self._y(r)))
        else:                                                                # 추첨 전: 가림막
            curtain = QRectF(self._x(0) - 14, top + 16, self._x(n - 1) - self._x(0) + 28, bottom - top - 32)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, 215))
            p.drawRoundedRect(curtain, 14, 14)
            f = QFont(font(), 14)
            f.setBold(True)
            p.setFont(f)
            p.setPen(QColor("#2E9E5B"))
            p.drawText(curtain, Qt.AlignCenter, T("✨ 기적을 일으키면 사다리가 나타나요"))
        if self.ladder is not None:                                          # 지나간 길
            for s in self.done_starts:
                self._draw_path(p, s, 1.0, 4.5, 170)
            if self.current is not None and self.phase == "tracing":
                self._draw_path(p, self.current, self.progress, 7, 255, head=True)
        f = QFont(font())
        f.setBold(True)
        f.setPixelSize(max(10, min(15, int(colw * 0.22))))
        fm = QFontMetricsF(f)
        p.setFont(f)
        ends = {self.ladder.end_of(s): s for s in self.done_starts} if self.ladder else {}
        for c in range(n):
            col = QColor(COLORS[c % len(COLORS)])
            chip = QRectF(self._x(c) - colw / 2 + 3, top - 46, colw - 6, 34)
            p.setPen(Qt.NoPen)
            p.setBrush(col)
            p.drawRoundedRect(chip, 9, 9)
            p.setPen(QColor("#FFFFFF"))
            p.drawText(chip, Qt.AlignCenter, fm.elidedText(self.top[c], Qt.ElideRight, chip.width() - 6))
            res = self.bottom[c] if c < len(self.bottom) else "?"
            box = QRectF(self._x(c) - colw / 2 + 3, bottom + 12, colw - 6, 34)
            opened = c in ends
            special = opened and not is_blank(res)
            p.setPen(QPen(QColor(COLORS[ends[c] % len(COLORS)]) if opened else QColor("#B9DEC6"), 2))
            p.setBrush(QColor("#FFF3B0") if special else QColor("#FFFFFF"))
            p.drawRoundedRect(box, 9, 9)
            p.setPen(QColor("#C8102E") if special else QColor("#22352A"))
            p.drawText(box, Qt.AlignCenter, fm.elidedText(res if opened else "?", Qt.ElideRight, box.width() - 6))
        p.end()

    def _draw_path(self, p: QPainter, start: int, upto: float, width: float, alpha: int, head: bool = False) -> None:
        pts = self.path_points(start)
        lens = [0.0]
        for a, b in zip(pts, pts[1:]):
            lens.append(lens[-1] + math.hypot(b.x() - a.x(), b.y() - a.y()))
        goal = lens[-1] * upto
        path = QPainterPath(pts[0])
        tip = pts[0]
        for (a, b), l0, l1 in zip(zip(pts, pts[1:]), lens, lens[1:]):
            if l1 <= goal:
                path.lineTo(b)
                tip = b
            else:
                k = (goal - l0) / max(1e-6, l1 - l0)
                tip = QPointF(a.x() + (b.x() - a.x()) * k, a.y() + (b.y() - a.y()) * k)
                path.lineTo(tip)
                break
        col = QColor(COLORS[start % len(COLORS)])
        col.setAlpha(alpha)
        p.setPen(QPen(col, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)
        if head:
            p.setPen(QPen(QColor("#FFFFFF"), 3))
            p.setBrush(QColor(COLORS[start % len(COLORS)]))
            p.drawEllipse(tip, 9, 9)
