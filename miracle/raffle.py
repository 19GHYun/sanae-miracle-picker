# -*- coding: utf-8 -*-
"""당첨자 뽑기 무대: 이름이 슬롯처럼 휙휙 돌다가 점점 느려지며 당첨자에서 멈춘다.
낮은 등수부터 한 명씩 발표하고, 아래 결과판에 등수별로 쌓인다.
"""
from __future__ import annotations

import random
import time
from typing import Callable

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

ROLL = 1.5            # 한 명 발표에 이름이 도는 시간 (초)
ROLL_TOP = 2.6        # 첫 등수(1등)는 더 길게 애태움
AUTO_NEXT = 1.2       # 자동 진행일 때 다음 발표까지


class RaffleStage(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.tiers: list[str] = []                 # 등수 이름 (첫 등수부터)
        self.board: dict[str, list[str]] = {}
        self.queue: list[tuple[str, str]] = []
        self.pool: list[str] = []
        self.current: tuple[str, str] | None = None   # (등수, 보여 주는 이름)
        self.phase = "idle"                        # idle / rolling / landed / done
        self.speed = 1.0
        self.auto = False
        self.flash = 0.0
        self._roll_start = 0.0
        self._roll = ROLL
        self._next_swap = 0.0
        self._winner = ""
        self._on_each: Callable[[str, str, int, int], None] | None = None
        self._on_done: Callable[[], None] | None = None
        self._total = 0
        self.on_roll: Callable[[float], None] | None = None   # 이름이 돌기 시작할 때 (초) — 드럼롤
        self.rng = random.Random()
        self.timer = QTimer(self, timeout=self._tick, interval=30)

    # ── 진행 ──
    def start(self, results: list[tuple[str, list[str]]], order: list[tuple[str, str]], pool: list[str],
              on_each: Callable[[str, str, int, int], None], on_done: Callable[[], None],
              auto: bool = False, speed: float = 1.0) -> None:
        self.tiers = [t for t, _ in results]
        self.board = {t: [] for t in self.tiers}
        self.queue = list(order)
        self.pool = pool or ["?"]
        self._on_each, self._on_done = on_each, on_done
        self.auto, self.speed = auto, speed
        self._total = len(order)
        self.phase = "landed"
        self.current = None
        self.next()

    @property
    def waiting(self) -> bool:
        """한 명 발표가 끝나고 다음 발표를 기다리는 중 (수동 진행)."""
        return self.phase == "landed" and bool(self.queue)

    @property
    def done_count(self) -> int:
        return self._total - len(self.queue) - (1 if self.phase == "rolling" else 0)

    def next(self) -> None:
        if self.phase == "rolling":
            return
        if not self.queue:
            self.phase = "done"
            self.update()
            return
        tier, self._winner = self.queue.pop(0)
        self._roll = ROLL_TOP if self.tiers and tier == self.tiers[0] else ROLL
        self.current = (tier, self.rng.choice(self.pool))
        self.phase = "rolling"
        self._roll_start = time.monotonic()
        self._next_swap = 0.0
        self.timer.start()
        if self.on_roll:
            self.on_roll(self._roll * self.speed)

    def stop(self) -> None:
        self.timer.stop()
        self.queue = []
        self.phase = "idle"

    def _tick(self) -> None:
        now = time.monotonic()
        self.flash = max(0.0, self.flash - 0.05)
        if self.phase == "rolling":
            u = (now - self._roll_start) / (self._roll * self.speed)
            if u >= 1.0:
                tier = self.current[0]
                self.current = (tier, self._winner)
                self.board.setdefault(tier, []).append(self._winner)
                self.phase, self.flash = "landed", 1.0
                n = self._total - len(self.queue)
                if self._on_each:
                    self._on_each(tier, self._winner, n, self._total)
                if not self.queue:
                    self.phase = "done"
                    if self._on_done:
                        self._on_done()
                elif self.auto:
                    QTimer.singleShot(int(AUTO_NEXT * 1000 * self.speed), self.next)
            elif now >= self._next_swap:                       # 점점 느려지며 이름이 바뀜
                self.current = (self.current[0], self.rng.choice(self.pool))
                self._next_swap = now + 0.05 + 0.25 * u * u
        elif self.flash <= 0:
            self.timer.stop()
        self.update()

    # ── 그리기 ──
    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        slot = QRectF(24, 20, w - 48, min(150.0, h * 0.34))
        self._slot(p, slot)
        self._board(p, QRectF(24, slot.bottom() + 18, w - 48, h - slot.bottom() - 30))
        p.end()

    def _slot(self, p: QPainter, r: QRectF) -> None:
        path = QPainterPath()
        path.addRoundedRect(r, 18, 18)
        g = QLinearGradient(0, r.top(), 0, r.bottom())
        g.setColorAt(0, QColor("#FFFFFF"))
        g.setColorAt(1, QColor("#EAF7EE"))
        p.setPen(QPen(QColor("#2E9E5B"), 3))
        p.setBrush(g)
        p.drawPath(path)
        tier, name = self.current if self.current else ("", "")
        f = QFont("Malgun Gothic", 13)
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor("#2E9E5B"))
        head = tier if tier else "당첨자 뽑기"
        if self._total and self.phase != "idle":
            head += f"   ({max(1, self._total - len(self.queue))} / {self._total})"
        p.drawText(r.adjusted(18, 10, -18, 0), Qt.AlignLeft | Qt.AlignTop, head)
        text = name or "준비되면 ✨ 기적을 일으키기!"
        size = 40 if name else 18
        f2 = QFont("Malgun Gothic")
        f2.setBold(True)
        f2.setPixelSize(size)
        while size > 14 and QFontMetricsF(f2).horizontalAdvance(text) > r.width() - 40:
            size -= 2
            f2.setPixelSize(size)
        p.setFont(f2)
        landed = self.phase in ("landed", "done") and bool(name)
        p.setPen(QColor("#C8102E") if landed else (QColor("#22352A") if name else QColor("#7A8B80")))
        p.drawText(r.adjusted(20, 26, -20, 0), Qt.AlignCenter, text)
        if self.flash > 0:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 246, 176, int(150 * self.flash)))
            p.drawPath(path)

    def _board(self, p: QPainter, r: QRectF) -> None:
        if not self.tiers or r.height() < 30:
            return
        path = QPainterPath()
        path.addRoundedRect(r, 14, 14)
        p.setPen(QPen(QColor(46, 158, 91, 90), 1.5))
        p.setBrush(QColor(255, 255, 255, 200))
        p.drawPath(path)
        rows = [(t, self.board.get(t, [])) for t in self.tiers]
        size = 15
        while size > 9:
            f = QFont("Malgun Gothic")
            f.setPixelSize(size)
            f.setBold(True)
            fm = QFontMetricsF(f)
            lines = self._wrap(rows, fm, r.width() - 40)
            if len(lines) * fm.height() * 1.35 <= r.height() - 24:
                break
            size -= 1
        p.setFont(f)
        y = r.top() + 12
        for kind, text in lines:
            if y + fm.height() > r.bottom() - 6:
                p.setPen(QColor("#7A8B80"))
                p.drawText(QRectF(r.left() + 20, y, r.width() - 40, fm.height()), Qt.AlignLeft, "… (결과 복사로 전체 보기)")
                break
            p.setPen(QColor("#2E9E5B") if kind == "tier" else QColor("#22352A"))
            p.drawText(QRectF(r.left() + 20, y, r.width() - 40, fm.height() * 1.3), Qt.AlignLeft | Qt.AlignVCenter, text)
            y += fm.height() * 1.35

    @staticmethod
    def _wrap(rows, fm: QFontMetricsF, width: float) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        for tier, names in rows:
            out.append(("tier", f"🏆 {tier}  ({len(names)}명)"))
            line = ""
            for n in names:
                piece = (", " if line else "   ") + n
                if line and fm.horizontalAdvance(line + piece) > width:
                    out.append(("name", line))
                    line = "   " + n
                else:
                    line += piece
            if line:
                out.append(("name", line))
        return out
