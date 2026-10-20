# -*- coding: utf-8 -*-
"""가챠 무대: 카드가 뒷면으로 깔리고 한 장씩 뒤집힌다. 가장 귀한 등급은 뒤집기 전에 금빛으로 애태운다."""
from __future__ import annotations

import math
import random
import time
from typing import Callable

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from .i18n import font

FLIP_EVERY = 0.34          # 한 장 뒤집는 간격
FLIP_TIME = 0.2            # 뒤집히는 동안
TEASE = 0.7                # 가장 귀한 등급: 뒤집기 전 금빛
RANK_COLORS = [("#F6C83A", "#E8833A"), ("#B07CE8", "#7B4FD0"), ("#5BA8F0", "#3D6FD8"), ("#8FC9A0", "#5A9E70")]


def _no_spaces(word: str) -> bool:
    """띄어쓰기 없이 쓰는 글(가나 · 한자)이면 글자 단위로 줄바꿈해도 됨. 한글 · 영어 단어는 되도록 안 끊음."""
    return any(0x3040 <= ord(ch) <= 0x30FF or 0x4E00 <= ord(ch) <= 0x9FFF for ch in word)   # 가나 · CJK 한자


class GachaStage(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.cards: list[tuple[str, str]] = []
        self.ranks: list[str] = []
        self.opened: list[bool] = []
        self.phase = "idle"
        self.speed = 1.0
        self.preview_n = 10
        self._t0 = 0.0
        self._done_at = 0.0
        self._times: list[float] = []         # 카드마다 뒤집기 시작하는 시각 (start 기준 초)
        self._on_flip: Callable[[int, str, str], None] | None = None
        self._on_done: Callable[[], None] | None = None
        self.rng = random.Random()
        self.timer = QTimer(self, timeout=self._tick, interval=16)

    @property
    def busy(self) -> bool:
        return self.phase == "running"

    def rank(self, rarity: str) -> int:
        return self.ranks.index(rarity) if rarity in self.ranks else len(self.ranks)

    def preview(self, n: int) -> None:
        if self.busy:
            return
        self.preview_n, self.cards, self.opened, self.phase = n, [], [], "idle"
        self.update()

    def start(self, cards: list[tuple[str, str]], ranks: list[str], on_flip: Callable[[int, str, str], None],
              on_done: Callable[[], None], speed: float = 1.0) -> None:
        self.cards, self.ranks, self.speed = cards, ranks, speed
        self.opened = [False] * len(cards)
        self._on_flip, self._on_done = on_flip, on_done
        t, times = 0.45, []
        for _, (rarity, _) in enumerate(cards):
            if self.rank(rarity) == 0 and len(ranks) > 1:
                t += TEASE
            times.append(t)
            t += FLIP_EVERY
        self._times = [x * speed for x in times]
        self.phase, self._t0 = "running", time.monotonic()
        self.timer.start()

    def skip(self) -> None:
        if not self.busy:
            return
        for i, (rarity, item) in enumerate(self.cards):
            if not self.opened[i]:
                self.opened[i] = True
                if self._on_flip:
                    self._on_flip(i, rarity, item)
        self._finish()

    def _finish(self) -> None:
        self._done_at = time.monotonic()
        self.phase = "done"
        self.timer.stop()
        self.update()
        if self._on_done:
            self._on_done()

    def _tick(self) -> None:
        t = time.monotonic() - self._t0
        for i, start in enumerate(self._times):
            if not self.opened[i] and t >= start + FLIP_TIME * self.speed / 2:
                self.opened[i] = True
                if self._on_flip:
                    self._on_flip(i, *self.cards[i])
        if all(self.opened) and t >= self._times[-1] + FLIP_TIME * self.speed + 0.3 * self.speed:
            self._finish()
            return
        self.update()

    # ── 그리기 ──
    def _slots(self, n: int) -> list[QRectF]:
        w, h = self.width(), self.height()
        cols = 1 if n == 1 else min(5, n)
        rows = math.ceil(n / cols)
        gap = 14
        cw = min((w - 40 - gap * (cols - 1)) / cols, (h - 40 - gap * (rows - 1)) / rows / 1.4, 200 if n == 1 else 130)
        ch = cw * 1.4
        out = []
        for i in range(n):
            r, c = divmod(i, cols)
            in_row = min(cols, n - r * cols)
            x0 = w / 2 - (in_row * cw + (in_row - 1) * gap) / 2
            y0 = h / 2 - (rows * ch + (rows - 1) * gap) / 2
            out.append(QRectF(x0 + c * (cw + gap), y0 + r * (ch + gap), cw, ch))
        return out

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        n = len(self.cards) or self.preview_n
        t = time.monotonic() - self._t0
        for i, r in enumerate(self._slots(n)):
            if i >= len(self.cards):
                self._back(p, r, 0.0)
                continue
            rarity, item = self.cards[i]
            start = self._times[i] if self.busy else -1.0
            tease = self.busy and not self.opened[i] and self.rank(rarity) == 0 and len(self.ranks) > 1 \
                and t >= start - TEASE * self.speed
            if self.busy and t < start:
                self._back(p, r, 1.0 if tease else 0.0)
                continue
            u = min(1.0, (t - start) / (FLIP_TIME * self.speed)) if self.busy else 1.0
            squash = abs(math.cos(u * math.pi))              # 1 → 0 → 1 (가운데서 앞면으로)
            p.save()
            p.translate(r.center())
            p.scale(max(0.04, squash), 1.0)
            p.translate(-r.center())
            if u < 0.5:
                self._back(p, r, 1.0 if tease else 0.0)
            else:
                self._front(p, r, rarity, item)
            p.restore()
        p.end()

    def _back(self, p: QPainter, r: QRectF, glow: float) -> None:
        if glow:
            pulse = 0.5 + 0.5 * math.sin(time.monotonic() * 14)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 210, 80, int(90 + 110 * pulse)))
            p.drawRoundedRect(r.adjusted(-8, -8, 8, 8), 16, 16)
        g = QLinearGradient(r.topLeft(), r.bottomRight())
        g.setColorAt(0, QColor("#2E9E5B"))
        g.setColorAt(1, QColor("#3D5BA9"))
        p.setPen(QPen(QColor("#FFFFFF"), 3))
        p.setBrush(g)
        p.drawRoundedRect(r, 12, 12)
        p.setPen(QPen(QColor(255, 255, 255, 120), 1.5))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(r.adjusted(7, 7, -7, -7), 8, 8)
        rad = min(r.width(), r.height()) * 0.24
        p.setBrush(QColor(255, 255, 255, 230))
        p.setPen(Qt.NoPen)
        p.drawEllipse(r.center(), rad, rad)
        f = QFont(font())
        f.setBold(True)
        f.setPixelSize(max(10, int(rad * 0.95)))
        p.setFont(f)
        p.setPen(QColor("#2E9E5B"))
        p.drawText(QRectF(r.center().x() - rad, r.center().y() - rad, rad * 2, rad * 2), Qt.AlignCenter, "奇")

    def _front(self, p: QPainter, r: QRectF, rarity: str, item: str) -> None:
        k = min(self.rank(rarity), len(RANK_COLORS) - 1)
        if len(self.ranks) <= 1:
            k = len(RANK_COLORS) - 1
        c1, c2 = RANK_COLORS[k]
        g = QLinearGradient(r.topLeft(), r.bottomRight())
        g.setColorAt(0, QColor(c1))
        g.setColorAt(1, QColor(c2))
        p.setPen(QPen(QColor("#FFFFFF"), 3))
        p.setBrush(g)
        p.drawRoundedRect(r, 12, 12)
        inner = r.adjusted(6, 30, -6, -10)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 235))
        p.drawRoundedRect(inner, 8, 8)
        f = QFont(font())
        f.setBold(True)
        f.setPixelSize(max(11, int(r.width() * 0.13)))
        p.setFont(f)
        p.setPen(QColor("#FFFFFF"))
        p.drawText(QRectF(r.left(), r.top() + 4, r.width(), 24), Qt.AlignCenter, rarity)
        size = max(10, int(r.width() * 0.17))
        f2 = QFont(font())
        f2.setBold(True)
        f2.setPixelSize(size)
        room = inner.width() - 6
        while True:                                       # 칸에 들어가게 (영어 단어는 되도록 안 끊기게) 줄임
            fm = QFontMetricsF(f2)
            lines = self._wrap(item, f2, room)
            tall = len(lines) * fm.height() > inner.height() - 6
            split = any(not _no_spaces(w) and fm.horizontalAdvance(w) > room for w in item.split(" "))
            if size <= 9 or not (tall or split):
                break
            size -= 1
            f2.setPixelSize(size)
        p.setFont(f2)
        p.setPen(QColor("#22352A"))
        p.drawText(inner, Qt.AlignCenter, "\n".join(lines))
        if k == 0 and len(self.ranks) > 1:                    # 가장 귀한 등급: 반짝이
            rng = random.Random(hash(item) & 0xFFFF)
            p.setPen(Qt.NoPen)
            for _ in range(6):
                tw = 0.5 + 0.5 * math.sin(time.monotonic() * 6 + rng.random() * 6)
                pt = QPointF(r.left() + rng.uniform(6, r.width() - 6), r.top() + rng.uniform(6, r.height() - 6))
                p.setBrush(QColor(255, 255, 255, int(120 + 135 * tw)))
                star = QPainterPath()
                for j in range(8):
                    rr = 5 if j % 2 == 0 else 1.6
                    a = math.pi / 4 * j
                    q = QPointF(pt.x() + math.sin(a) * rr, pt.y() - math.cos(a) * rr)
                    if j == 0:
                        star.moveTo(q)
                    else:
                        star.lineTo(q)
                star.closeSubpath()
                p.drawPath(star)
            if not self.busy and time.monotonic() - self._done_at < 5.0:   # 다 뒤집은 뒤 5초 동안만 반짝
                QTimer.singleShot(60, self.update)

    @staticmethod
    def _wrap(text: str, f: QFont, width: float) -> list[str]:
        fm = QFontMetricsF(f)
        if fm.horizontalAdvance(text) <= width:
            return [text]
        words, lines, cur = text.split(" "), [], ""
        for w in words:
            cand = f"{cur} {w}".strip()
            if fm.horizontalAdvance(cand) <= width or not cur:
                cur = cand
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
        out = []
        for ln in lines:                                  # 띄어쓰기 없는 긴 이름은 글자 단위로
            while fm.horizontalAdvance(ln) > width and len(ln) > 1:
                k = len(ln)
                while k > 1 and fm.horizontalAdvance(ln[:k]) > width:
                    k -= 1
                out.append(ln[:k])
                ln = ln[k:]
            out.append(ln)
        return out
