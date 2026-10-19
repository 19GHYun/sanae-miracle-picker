# -*- coding: utf-8 -*-
"""주사위 · 동전 · 숫자 무대: 굴러가는 동안 면이 휙휙 바뀌다가(점점 느리게) 결과에서 멈춘다."""
from __future__ import annotations

import math
import random
import time
from typing import Callable

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QWidget
from .i18n import T, font

ROLL_TIME = 1.6
PIPS = {1: [(0, 0)], 2: [(-1, -1), (1, 1)], 3: [(-1, -1), (0, 0), (1, 1)], 4: [(-1, -1), (1, -1), (-1, 1), (1, 1)],
        5: [(-1, -1), (1, -1), (0, 0), (-1, 1), (1, 1)], 6: [(-1, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (1, 1)]}


class DiceStage(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.kind = "dice"
        self.sides = 6
        self.lo, self.hi = 1, 100
        self.values: list = []
        self.faces: list = []
        self.phase = "idle"
        self.speed = 1.0
        self._t0 = 0.0
        self._next = 0.0
        self._on_done: Callable[[], None] | None = None
        self.rng = random.Random()
        self.timer = QTimer(self, timeout=self._tick, interval=30)

    @property
    def busy(self) -> bool:
        return self.phase == "rolling"

    def preview(self, kind: str, count: int, sides: int, lo: int, hi: int) -> None:
        if self.busy:
            return
        self.kind, self.sides, self.lo, self.hi = kind, sides, lo, hi
        self.values, self.faces, self.phase = [], [None] * max(1, count), "idle"
        self.update()

    def start(self, kind: str, values: list, sides: int, lo: int, hi: int, on_done: Callable[[], None],
              speed: float = 1.0) -> None:
        self.kind, self.values, self.sides, self.lo, self.hi = kind, values, sides, lo, hi
        self.faces = [self._random_face() for _ in values]
        self._on_done, self.speed = on_done, speed
        self.phase, self._t0, self._next = "rolling", time.monotonic(), 0.0
        self.timer.start()

    def skip(self) -> None:
        if self.busy:
            self._land()

    def _random_face(self):
        if self.kind == "coin":
            return self.rng.choice([T("앞"), T("뒤")])
        if self.kind == "number":
            return self.rng.randint(min(self.lo, self.hi), max(self.lo, self.hi))
        return self.rng.randint(1, self.sides)

    def _land(self) -> None:
        self.faces, self.phase = list(self.values), "done"
        self.timer.stop()
        self.update()
        if self._on_done:
            self._on_done()

    def _tick(self) -> None:
        now = time.monotonic()
        u = (now - self._t0) / (ROLL_TIME * self.speed)
        if u >= 1.0:
            self._land()
            return
        if now >= self._next:
            self.faces = [self._random_face() for _ in self.values]
            self._next = now + 0.04 + 0.22 * u * u
        self.update()

    # ── 그리기 ──
    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        n = max(1, len(self.faces))
        w, h = self.width(), self.height() - 70
        cols = min(n, 5)
        rows = math.ceil(n / cols)
        size = min(150.0, (w - 40) / cols - 16, (h - 40) / rows - 16)
        wobble = self.phase == "rolling"
        for i, face in enumerate(self.faces or [None]):
            cx = w / 2 + ((i % cols) - (min(n - (i // cols) * cols, cols) - 1) / 2) * (size + 16)
            cy = 30 + h / 2 + ((i // cols) - (rows - 1) / 2) * (size + 16)
            angle = math.sin(time.monotonic() * 20 + i) * 12 if wobble else 0.0
            p.save()
            p.translate(cx, cy)
            p.rotate(angle)
            r = QRectF(-size / 2, -size / 2, size, size)
            if self.kind == "coin":
                self._coin(p, r, face)
            elif self.kind == "number":
                self._card(p, r, face)
            else:
                self._die(p, r, face)
            p.restore()
        if self.phase == "done" and self.kind == "dice" and len(self.values) > 1:
            f = QFont(font())
            f.setBold(True)
            f.setPixelSize(26)
            p.setFont(f)
            p.setPen(QColor("#2E9E5B"))
            p.drawText(QRectF(0, self.height() - 64, w, 44), Qt.AlignCenter, T("합계  {v1}", v1=sum(self.values)))
        p.end()

    def _die(self, p: QPainter, r: QRectF, face) -> None:
        p.setPen(QPen(QColor("#5B4636"), 3))
        p.setBrush(QColor("#FFFFFF"))
        p.drawRoundedRect(r, r.width() * 0.18, r.width() * 0.18)
        if face is None:
            self._text(p, r, "?", r.width() * 0.5, "#9FB0A6")
            return
        if self.sides == 6:
            dot = r.width() * 0.09
            for dx, dy in PIPS[int(face)]:
                p.setPen(Qt.NoPen)
                p.setBrush(QColor("#C8102E") if face == 1 else QColor("#22352A"))
                p.drawEllipse(QPointF(dx * r.width() * 0.27, dy * r.width() * 0.27), dot * (1.4 if face == 1 else 1), dot * (1.4 if face == 1 else 1))
            return
        self._text(p, r, str(face), r.width() * (0.45 if face < 100 else 0.36), "#22352A")
        small = QRectF(r.left(), r.bottom() - r.height() * 0.26, r.width(), r.height() * 0.2)
        self._text(p, small, f"d{self.sides}", r.width() * 0.13, "#7A8B80")

    def _coin(self, p: QPainter, r: QRectF, face) -> None:
        g = QRadialGradient(QPointF(r.center().x() - r.width() * 0.15, r.center().y() - r.height() * 0.15), r.width() * 0.6)
        g.setColorAt(0, QColor("#FFE58A"))
        g.setColorAt(1, QColor("#D9A21E"))
        p.setPen(QPen(QColor("#9A6B10"), 3))
        p.setBrush(g)
        p.drawEllipse(r)
        p.setPen(QPen(QColor(255, 255, 255, 120), 2))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(r.adjusted(r.width() * 0.1, r.width() * 0.1, -r.width() * 0.1, -r.width() * 0.1))
        self._text(p, r, "?" if face is None else str(face), r.width() * 0.36, "#7A4E08")

    def _card(self, p: QPainter, r: QRectF, face) -> None:
        p.setPen(QPen(QColor("#2E9E5B"), 3))
        p.setBrush(QColor("#FFFFFF"))
        p.drawRoundedRect(r, 16, 16)
        text = "?" if face is None else str(face)
        self._text(p, r, text, r.width() * (0.42 if len(text) <= 3 else 0.3), "#22352A" if face is not None else "#9FB0A6")

    @staticmethod
    def _text(p: QPainter, r: QRectF, text: str, px: float, color: str) -> None:
        f = QFont(font())
        f.setBold(True)
        f.setPixelSize(max(9, int(px)))
        while f.pixelSize() > 9 and QFontMetricsF(f).horizontalAdvance(text) > r.width() * 0.86:
            f.setPixelSize(f.pixelSize() - 2)
        p.setFont(f)
        p.setPen(QColor(color))
        p.drawText(r, Qt.AlignCenter, text)
