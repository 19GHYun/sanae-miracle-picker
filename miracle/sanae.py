# -*- coding: utf-8 -*-
"""사나에: 추첨 무대 옆에서 고헤이를 휘두르고(돌리는 중), 폴짝 뛰며 기뻐하고(발표), 말풍선으로 말한다.

그림은 miracle/sprites/<키>/ (Hokora 와 같은 형식: 그림 + manifest.json 의 발 위치).
"""
from __future__ import annotations

import json
import math
import random
import re
import time
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QImage, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget
from .i18n import T, font

SPRITE_DIR = Path(__file__).resolve().parent / "sprites"


class Sprites:
    """캐릭터 그림 한 벌: 이름 → (그림, 발 위치)."""

    def __init__(self, key: str):
        folder = SPRITE_DIR / key
        m = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        self.standing = float(m["standing_height"])
        self.facing = int(m.get("facing", 1))
        self.frames: dict[str, tuple[QImage, QPointF]] = {}
        for name, (ax, ay) in m["frames"].items():
            img = QImage(str(folder / f"{name}.png"))
            if not img.isNull():
                self.frames[name] = (img, QPointF(ax, ay))

    def seq(self, kind: str) -> list[str]:
        """이 동작의 그림들 (kind_0, kind_1 … 차례로, 없으면 kind 한 장, 그것도 없으면 idle)."""
        names = sorted((n for n in self.frames if re.fullmatch(rf"{kind}_\d+", n)), key=lambda n: int(n.rsplit("_", 1)[1]))
        if names:
            return names
        if kind in self.frames:
            return [kind]
        return self.seq("idle") if kind != "idle" else [next(iter(self.frames))]


IDLE_LINES = [T("오늘은 어떤 기적이 일어날까요?"), T("준비되면 버튼을 눌러 주세요!"), T("모리야의 바람이 함께해요~")]
SPIN_LINES = [T("바람이여~ 기적을!"), T("에잇! 기적을 일으켜 볼게요!"), T("두근두근…!")]


class SanaeWidget(QWidget):
    """사나에 + 말풍선. 동작: idle / spin / happy / oops. 클릭은 통과."""

    W, H = 300, 330
    BUBBLE_H = 92

    def __init__(self, parent: QWidget, height: float = 200.0):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(self.W, self.H)
        self.sp = Sprites("sanae")
        self.k = height / self.sp.standing
        self.mode = "idle"
        self.mode_at = time.monotonic()
        self.bubble = ""
        self.bubble_until = 0.0
        self.blink_at = time.monotonic() + 3.0
        self.f = 1.0                     # 크기 배율 (방송 창처럼 무대가 크면 같이 커짐)
        self.shadow = True               # 크로마키일 땐 반투명 그림자를 안 그림
        self.timer = QTimer(self, timeout=self.update, interval=50)
        self.timer.start()

    def set_scale(self, f: float) -> None:
        if abs(f - self.f) > 0.01:
            self.f = f
            self.setFixedSize(round(self.W * f), round(self.H * f))
            self.update()

    def set_mode(self, mode: str, line: str | None = None, seconds: float = 3.0) -> None:
        self.mode, self.mode_at = mode, time.monotonic()
        if line:
            self.say(line, seconds)

    def say(self, text: str, seconds: float = 3.0) -> None:
        self.bubble, self.bubble_until = text, time.monotonic() + seconds

    def frame(self) -> tuple[str, float]:
        """지금 그릴 그림 이름과 위아래 흔들림."""
        now = time.monotonic()
        t = now - self.mode_at
        if self.mode == "spin":
            seq = self.sp.seq("skill")
            return seq[int(t / 0.22) % len(seq)], -abs(math.sin(t * 9)) * 3
        if self.mode == "happy":
            jump = self.sp.seq("happy")
            if t < 0.9:
                return jump[min(len(jump) - 1, int(t / 0.9 * len(jump)))], 0.0
            if t < 3.2:
                wave = self.sp.seq("wave")
                return wave[int(t / 0.35) % len(wave)], 0.0
            self.mode, self.mode_at = "idle", now
        if self.mode == "oops":
            if t < 2.2:
                return self.sp.seq("caught")[0], math.sin(t * 30) * 1.5 if t < 0.4 else 0.0
            self.mode, self.mode_at = "idle", now
        if self.blink_at <= now < self.blink_at + 0.15 and "blink" in self.sp.frames:
            return "blink", 0.0
        if now >= self.blink_at + 0.15:
            self.blink_at = now + random.uniform(2.5, 5.0)
        idle = self.sp.seq("idle")
        return idle[int(now / 1.6) % len(idle)], math.sin(now * 2.2) * 1.2

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        name, dy = self.frame()
        img, anchor = self.sp.frames[name]
        p.scale(self.f, self.f)
        k = self.k
        fx, fy = self.W / 2, self.H - 10
        if self.shadow:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0, 40))
            p.drawEllipse(QRectF(fx - 46, fy - 7, 92, 14))
        p.drawImage(QRectF(fx - anchor.x() * k, fy + dy - anchor.y() * k, img.width() * k, img.height() * k), img)
        if self.bubble and time.monotonic() < self.bubble_until:
            self._bubble(p)
        p.end()

    def _bubble(self, p: QPainter) -> None:
        f = QFont(font(), 11)
        f.setBold(True)
        fm = QFontMetricsF(f)
        left, right = 34.0, self.W - 4.0                 # 무대 안에 보이는 부분 (사나에 칸은 무대 왼쪽 밖으로 30 나가 있음)
        text_w = min(right - left - 28, fm.horizontalAdvance(self.bubble) + 4)
        wrap = Qt.TextWordWrap
        rect = fm.boundingRect(QRectF(0, 0, text_w, 200), wrap | Qt.AlignCenter, self.bubble)
        if rect.width() > text_w + 1:                     # 띄어쓸 데가 없는 긴 글(일본어 등)은 아무 데서나 줄바꿈
            wrap = Qt.TextWrapAnywhere
            rect = fm.boundingRect(QRectF(0, 0, text_w, 200), wrap | Qt.AlignCenter, self.bubble)
        w, h = rect.width() + 28, rect.height() + 18
        cx = min(right - w / 2, max(left + w / 2, self.W / 2))
        r = QRectF(cx - w / 2, max(4.0, self.BUBBLE_H - h - 10), w, h)
        path = QPainterPath()
        path.addRoundedRect(r, 12, 12)
        tail = QPainterPath(QPointF(self.W / 2 - 8, r.bottom() - 1))
        tail.lineTo(self.W / 2 + 8, r.bottom() - 1)
        tail.lineTo(self.W / 2 + 2, r.bottom() + 11)
        tail.closeSubpath()
        p.setPen(QPen(QColor("#2E9E5B"), 1.6))
        p.setBrush(QColor(255, 255, 255, 245))
        p.drawPath(path.united(tail))
        p.setFont(f)
        p.setPen(QColor("#22352A"))
        p.drawText(r, Qt.AlignCenter | wrap, self.bubble)
