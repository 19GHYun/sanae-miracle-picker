# -*- coding: utf-8 -*-
"""룰렛: 칸 넓이 = 가중치. 결과(칸·칸 안 위치)는 core.spin 이 시드로 먼저 정하고, 바퀴는 그 자리에 서도록 감속 회전한다.

각도는 "12시 방향에서 시계 방향" 으로 잰다. 바늘은 12시에 고정, 바퀴가 rot 만큼 돌아 있으면
바늘 아래 지점 = (-rot) mod 360.
"""
from __future__ import annotations

import math
import time
from typing import Callable

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPainterPath, QPen, QRadialGradient
from PySide6.QtWidgets import QWidget

from .core import Entry

PALETTE = ["#4CB878", "#3D7DD8", "#F2C230", "#E8657A", "#8E6CD8", "#3FB7C4",
           "#F28C38", "#7FBF3F", "#D8579A", "#5B8DEF", "#E0A23A", "#4FA3A0"]
TURNS = 6


def ease_out(u: float) -> float:
    return 1 - (1 - u) ** 4


class WheelWidget(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.entries: list[Entry] = []
        self.rot = 0.0
        self.spinning = False
        self.winner: int | None = None
        self.kick = 0.0                    # 바늘이 칸 경계에 걸려 튀는 정도
        self._from = self._to = 0.0
        self._start = 0.0
        self._dur = 1.0
        self._done: Callable[[int], None] | None = None
        self._target = -1
        self._under = -1
        self._won_at = 0.0
        self.timer = QTimer(self, timeout=self._tick, interval=16)

    # ── 목록 ──
    def set_entries(self, entries: list[Entry]) -> None:
        if not self.spinning:
            self.entries = list(entries)
            self.winner = None
            self.update()

    def spans(self) -> list[tuple[float, float]]:
        """칸마다 (시작 각, 넓이) — 12시에서 시계 방향, 바퀴가 돌기 전 기준."""
        total = sum(e.weight for e in self.entries) or 1
        out, a = [], 0.0
        for e in self.entries:
            w = 360.0 * e.weight / total
            out.append((a, w))
            a += w
        return out

    def under_pointer(self) -> int:
        if not self.entries:
            return -1
        at = (-self.rot) % 360.0
        for i, (a, w) in enumerate(self.spans()):
            if a <= at < a + w:
                return i
        return len(self.entries) - 1

    # ── 돌리기 ──
    def spin_to(self, idx: int, frac: float, seconds: float, done: Callable[[int], None]) -> None:
        a, w = self.spans()[idx]
        target = a + w * frac
        delta = (-target - self.rot) % 360.0 + 360.0 * TURNS
        self._from, self._to = self.rot, self.rot + delta
        self._start, self._dur = time.monotonic(), max(0.05, seconds)
        self._done, self._target = done, idx
        self.spinning, self.winner = True, None
        self._under = self.under_pointer()
        self.timer.start()

    def _tick(self) -> None:
        u = min(1.0, (time.monotonic() - self._start) / self._dur)
        self.rot = self._from + (self._to - self._from) * ease_out(u)
        under = self.under_pointer()
        if under != self._under:
            self._under = under
            self.kick = 1.0
        self.kick = max(0.0, self.kick - 0.18)
        if u >= 1.0:
            self.timer.stop()
            self.rot %= 360.0
            self.spinning, self.winner, self.kick = False, self._target, 0.0
            self._won_at = time.monotonic()
            done, self._done = self._done, None
            if done:
                done(self._target)
        self.update()

    # ── 그리기 ──
    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        side = min(self.width(), self.height()) - 16
        R = side / 2 - 14
        c = QPointF(self.width() / 2, self.height() / 2 + 8)
        if R < 40:
            p.end()
            return
        p.setPen(Qt.NoPen)                                            # 그림자
        p.setBrush(QColor(0, 0, 0, 35))
        p.drawEllipse(QPointF(c.x() + 4, c.y() + 8), R + 12, R + 12)
        p.setBrush(QColor("#2E6B48"))                                 # 테두리
        p.drawEllipse(c, R + 12, R + 12)
        if not self.entries:
            p.setBrush(QColor("#F4FBF6"))
            p.drawEllipse(c, R, R)
            f = QFont("Malgun Gothic", 13)
            f.setBold(True)
            p.setFont(f)
            p.setPen(QColor("#5A6B60"))
            p.drawText(QRectF(c.x() - R, c.y() - 40, 2 * R, 80), Qt.AlignCenter, "목록에 항목을 넣어 주세요")
            p.end()
            return
        rect = QRectF(c.x() - R, c.y() - R, 2 * R, 2 * R)
        spans = self.spans()
        n = len(spans)
        colors = [PALETTE[i % len(PALETTE)] for i in range(n)]
        if n > 1 and colors[-1] == colors[0]:                          # 처음·끝 칸이 같은 색이면
            colors[-1] = PALETTE[(n + 1) % len(PALETTE)]
        for i, (a, w) in enumerate(spans):
            start = a + self.rot
            path = QPainterPath(c)
            path.arcTo(rect, 90 - start, -w)
            path.closeSubpath()
            col = QColor(colors[i])
            if self.winner is not None and i != self.winner:
                col = col.lighter(135)
                col.setAlpha(150)
            p.setPen(QPen(QColor(255, 255, 255, 200), 1.5 if n < 60 else 0.6))
            p.setBrush(col)
            p.drawPath(path)
        for i, (a, w) in enumerate(spans):                            # 글자
            self._label(p, c, R, a + self.rot, w, self.entries[i].name, i == self.winner)
        if self.winner is not None:                                   # 당첨 칸 테두리 반짝
            a, w = spans[self.winner]
            path = QPainterPath(c)
            path.arcTo(rect, 90 - (a + self.rot), -w)
            path.closeSubpath()
            shining = time.monotonic() - self._won_at < 4.0          # 멈춘 뒤 4초 동안만 반짝반짝
            glow = 0.5 + 0.5 * math.sin(time.monotonic() * 6) if shining else 1.0
            p.setPen(QPen(QColor(255, 255, 255, int(160 + 95 * glow)), 4))
            p.setBrush(Qt.NoBrush)
            p.drawPath(path)
            if shining:
                QTimer.singleShot(40, self.update)
        self._rim_lights(p, c, R)
        hub = QRadialGradient(c, R * 0.16)                            # 가운데
        hub.setColorAt(0, QColor("#FFFFFF"))
        hub.setColorAt(1, QColor("#E6F5EA"))
        p.setPen(QPen(QColor("#2E6B48"), 3))
        p.setBrush(hub)
        p.drawEllipse(c, R * 0.15, R * 0.15)
        f = QFont("Malgun Gothic", max(8, int(R * 0.07)))
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor("#2E9E5B"))
        p.drawText(QRectF(c.x() - R * 0.15, c.y() - R * 0.15, R * 0.3, R * 0.3), Qt.AlignCenter, "奇跡")
        self._pointer(p, c, R)

    def _label(self, p: QPainter, c: QPointF, R: float, start: float, w: float, text: str, win: bool) -> None:
        h = 2 * R * 0.62 * math.sin(math.radians(min(w, 179.0)) / 2)   # 글자가 들어갈 칸 높이
        if h < 9:
            return
        px = max(9, min(int(h * 0.55), 22, int(R * 0.09)))
        f = QFont("Malgun Gothic")
        f.setPixelSize(px)
        f.setBold(True)
        fm = QFontMetricsF(f)
        room = R * 0.68
        shown = fm.elidedText(text, Qt.ElideRight, room)
        p.save()
        p.translate(c)
        p.rotate(start + w / 2 - 90)
        p.setFont(f)
        p.setPen(QColor(0, 0, 0, 70))
        box = QRectF(R * 0.22, -px, room, px * 2)
        p.drawText(box.translated(1, 1), Qt.AlignRight | Qt.AlignVCenter, shown)
        p.setPen(QColor("#FFFFFF") if not win else QColor("#FFFDE7"))
        p.drawText(box, Qt.AlignRight | Qt.AlignVCenter, shown)
        p.restore()

    def _rim_lights(self, p: QPainter, c: QPointF, R: float) -> None:
        n = 24
        phase = int(time.monotonic() * (10 if self.spinning else 2))
        p.setPen(Qt.NoPen)
        for i in range(n):
            a = math.radians(i * 360 / n)
            on = (i + phase) % 2 == 0
            p.setBrush(QColor("#FFF6B0") if on else QColor(255, 255, 255, 120))
            p.drawEllipse(QPointF(c.x() + math.sin(a) * (R + 6), c.y() - math.cos(a) * (R + 6)), 3.2, 3.2)

    def _pointer(self, p: QPainter, c: QPointF, R: float) -> None:
        tip = QPointF(c.x(), c.y() - R + 16)
        p.save()
        p.translate(c.x(), c.y() - R - 18)
        p.rotate(-self.kick * 16)
        path = QPainterPath(QPointF(-17, 0))
        path.lineTo(17, 0)
        path.lineTo(0, tip.y() - (c.y() - R - 18))
        path.closeSubpath()
        p.setPen(QPen(QColor("#FFFFFF"), 3))
        p.setBrush(QColor("#D9412E"))
        p.drawPath(path)
        p.setBrush(QColor("#FFFFFF"))
        p.setPen(QPen(QColor("#D9412E"), 3))
        p.drawEllipse(QPointF(0, 0), 9, 9)
        p.restore()
