# -*- coding: utf-8 -*-
"""신님 카메오: 좋은 결과가 나오면 스와코나 카나코가 무대 오른쪽 아래에서 쏙 올라와 축하하고 내려간다.

누가 나올지 · 나올지 말지는 보기 좋으라고 고르는 것이라 추첨 결과(시드)와는 상관없다.
그림은 miracle/sprites/<suwako|kanako>/ (idle_0 · blink · thumbs · cheer).
"""
from __future__ import annotations

import math
import random
import time

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from .i18n import T, font
from .sanae import SPRITE_DIR, Sprites

LENGTH = 3.6                       # 올라와서 내려갈 때까지 (초)
GODS = {                           # 키: (말풍선 테두리 색, 대사들)
    "suwako": ("#5B5BA8", (T("케로케로~ 기적이네!"), T("아~우! 축하해~"))),
    "kanako": ("#B03A3A", (T("훌륭한 신앙이다!"), T("바람과 함께 축복을!"))),
}


class CameoWidget(QWidget):
    W, H = 240, 290
    FIGURE = 165                   # 서 있는 키 (사나에는 200)

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(self.W, self.H)
        self.sprites = {key: Sprites(key) for key in GODS if (SPRITE_DIR / key / "manifest.json").exists()}
        self.who = ""
        self.line = ""
        self.started = 0.0
        self.length = LENGTH
        self.f = 1.0
        self.timer = QTimer(self, timeout=self._tick, interval=30)
        self.hide()

    @property
    def active(self) -> bool:
        return self.isVisible()

    def set_scale(self, f: float) -> None:
        if abs(f - self.f) > 0.01:
            self.f = f
            self.setFixedSize(round(self.W * f), round(self.H * f))

    def play(self, who: str | None = None, speed: float = 1.0) -> bool:
        if not self.sprites:
            return False
        self.who = who if who in self.sprites else random.choice(sorted(self.sprites))
        self.line = random.choice(GODS[self.who][1])
        self.length = LENGTH * speed
        self.started = time.monotonic()
        self.raise_()                                   # 컷인보다 위에
        self.show()
        self.timer.start()
        self.update()
        return True

    def finish(self) -> None:
        self.timer.stop()
        self.hide()

    def _tick(self) -> None:
        if time.monotonic() - self.started >= self.length:
            self.finish()
            return
        self.update()

    def pose(self, u: float) -> tuple[str, float]:
        """진행 정도 u (0~1) → 그림 이름과 위아래 흔들림: 만세(통통) → 엄지척 (중간에 눈 깜빡)."""
        if u < 0.45:
            return "cheer", -abs(math.sin(u * 40)) * 4
        if 0.66 <= u < 0.70:
            return "blink", 0.0
        return "thumbs", 0.0

    def paintEvent(self, _e) -> None:
        sp = self.sprites.get(self.who)
        if sp is None:
            return
        u = min(1.0, (time.monotonic() - self.started) / max(0.01, self.length))
        if u < 0.12:                                    # 쏙 올라옴 · 머묾 · 내려감
            shown = 1 - (1 - u / 0.12) ** 3
        elif u > 0.86:
            shown = 1 - ((u - 0.86) / 0.14) ** 2
        else:
            shown = 1.0
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.scale(self.f, self.f)
        name, bob = self.pose(u)
        img, anchor = sp.frames.get(name) or sp.frames["idle_0"]
        k = self.FIGURE / sp.standing
        fx, fy = self.W * 0.58, self.H - 4 + (1 - shown) * (self.FIGURE + 20)
        p.drawImage(QRectF(fx - anchor.x() * k, fy + bob - anchor.y() * k, img.width() * k, img.height() * k), img)
        if 0.10 < u < 0.86:
            self._bubble(p, GODS[self.who][0], fy - self.FIGURE - 8)
        p.end()

    def _bubble(self, p: QPainter, color: str, bottom: float) -> None:
        f = QFont(font(), 11)
        f.setBold(True)
        fm = QFontMetricsF(f)
        text_w = min(self.W - 36, fm.horizontalAdvance(self.line) + 4)
        wrap = Qt.TextWordWrap
        rect = fm.boundingRect(QRectF(0, 0, text_w, 120), wrap | Qt.AlignCenter, self.line)
        if rect.width() > text_w + 1:                   # 띄어쓸 데가 없는 긴 글(일본어)은 아무 데서나 줄바꿈
            wrap = Qt.TextWrapAnywhere
            rect = fm.boundingRect(QRectF(0, 0, text_w, 120), wrap | Qt.AlignCenter, self.line)
        w, h = rect.width() + 24, rect.height() + 14
        cx = min(self.W - 4 - w / 2, max(4 + w / 2, self.W * 0.5))
        r = QRectF(cx - w / 2, max(2.0, bottom - h - 10), w, h)
        path = QPainterPath()
        path.addRoundedRect(r, 11, 11)
        tail = QPainterPath(QPointF(self.W * 0.58 - 7, r.bottom() - 1))
        tail.lineTo(self.W * 0.58 + 7, r.bottom() - 1)
        tail.lineTo(self.W * 0.58 + 1, r.bottom() + 10)
        tail.closeSubpath()
        p.setPen(QPen(QColor(color), 1.8))
        p.setBrush(QColor(255, 255, 255, 245))
        p.drawPath(path.united(tail))
        p.setFont(f)
        p.setPen(QColor("#22352A"))
        p.drawText(r, Qt.AlignCenter | wrap, self.line)
