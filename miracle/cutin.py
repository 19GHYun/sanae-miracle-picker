# -*- coding: utf-8 -*-
"""결과 발표 컷인: 초록·파랑 띠가 미끄러져 들어오고, 사나에와 "✨ 기적 발생! ✨" + 결과, 색종이가 흩날린다.
무대 위에 겹쳐 그리는 자식 위젯. 누르면 바로 닫힌다.
"""
from __future__ import annotations

import math
import random
import time

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from .i18n import font
from .sanae import Sprites

CONFETTI = ["#4CB878", "#3D7DD8", "#F2C230", "#E8657A", "#FFFFFF", "#8E6CD8", "#3FB7C4"]
LENGTH = 2.8


class MiracleCutIn(QWidget):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.sp = Sprites("sanae")
        self.title = ""
        self.text = ""
        self.started = 0.0
        self.length = LENGTH
        self.bits: list[list[float]] = []
        self._hidden: QWidget | None = None
        self.timer = QTimer(self, timeout=self._tick, interval=16)
        self.hide()

    def play(self, title: str, text: str, speed: float = 1.0, burst: int = 90,
             hide: QWidget | None = None) -> None:
        """hide: 컷인 동안 숨길 위젯 (무대의 사나에 — 컷인에도 사나에가 나오니까)."""
        self.title, self.text = title, text
        self.length = LENGTH * speed
        self.started = time.monotonic()
        self.setGeometry(self.parentWidget().rect())            # 크기를 먼저 잡아야 색종이가 화면 전체에
        rng = random.Random()
        w, h = max(1, self.width()), max(1, self.height())
        self.bits = [[rng.uniform(0, w), rng.uniform(-h * 0.6, -10), rng.uniform(-60, 60), rng.uniform(80, 220),
                      rng.uniform(0, 360), rng.uniform(-300, 300), rng.randrange(len(CONFETTI)), rng.randrange(3)]
                     for _ in range(burst)]
        self._hidden = hide
        if hide is not None:
            hide.hide()
        self.raise_()
        self.show()
        self.timer.start()

    def finish(self) -> None:
        self.timer.stop()
        self.hide()
        if self._hidden is not None:
            self._hidden.show()
            self._hidden = None

    @property
    def active(self) -> bool:
        return self.isVisible()

    def _tick(self) -> None:
        t = time.monotonic() - self.started
        if t >= self.length:
            self.finish()
            return
        dt = 0.016
        for b in self.bits:
            b[0] += b[2] * dt
            b[1] += b[3] * dt
            b[4] += b[5] * dt
            b[2] += math.sin(t * 3 + b[6]) * 4
        self.update()

    def mousePressEvent(self, _e) -> None:
        self.finish()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        t = time.monotonic() - self.started
        u = t / max(0.01, self.length)
        fade = min(1.0, (1 - u) / 0.18)                         # 끝 무렵 흐려짐
        p.setOpacity(max(0.0, fade))
        w, h = self.width(), self.height()
        slide = 1 - (1 - min(1.0, t / 0.35)) ** 3                # 띠가 미끄러져 들어옴
        band_h = min(170.0, h * 0.42)
        band = QRectF(-w + slide * w, h / 2 - band_h / 2, w, band_h)
        path = QPainterPath()
        path.moveTo(band.left() + 40, band.top())
        path.lineTo(band.right(), band.top())
        path.lineTo(band.right() - 40, band.bottom())
        path.lineTo(band.left(), band.bottom())
        path.closeSubpath()
        g = QLinearGradient(band.left(), 0, band.right(), 0)
        g.setColorAt(0, QColor(46, 158, 91, 235))
        g.setColorAt(1, QColor(61, 91, 169, 235))
        p.setPen(Qt.NoPen)
        p.setBrush(g)
        p.drawPath(path)
        p.setPen(QPen(QColor(255, 255, 255, 200), 3))
        p.drawLine(QPointF(band.left() + 40, band.top() + 6), QPointF(band.right(), band.top() + 6))
        p.drawLine(QPointF(band.left(), band.bottom() - 6), QPointF(band.right() - 40, band.bottom() - 6))
        seq = self.sp.seq("happy")                               # 사나에
        img, anchor = self.sp.frames[seq[min(len(seq) - 1, int(t / 0.18) % len(seq))]]
        k = band_h * 1.25 / self.sp.standing
        sx = band.left() + w * 0.16
        p.drawImage(QRectF(sx - anchor.x() * k, band.bottom() + 8 - anchor.y() * k, img.width() * k, img.height() * k), img)
        tx = band.left() + w * 0.30
        tw = w * 0.66
        f = QFont(font(), 14)
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor("#FFF6B0"))
        p.drawText(QRectF(tx, band.top() + 12, tw, 30), Qt.AlignLeft | Qt.AlignVCenter, self.title)
        size = int(band_h * 0.36)
        big = QFont(font())
        big.setBold(True)
        big.setPixelSize(size)
        while size > 16 and QFontMetricsF(big).horizontalAdvance(self.text) > tw - 10:
            size -= 2
            big.setPixelSize(size)
        text_path = QPainterPath()
        fm = QFontMetricsF(big)
        text_path.addText(QPointF(tx, band.center().y() + fm.ascent() / 2 + 10), big, self.text)
        p.strokePath(text_path, QPen(QColor(20, 50, 35, 220), 6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.fillPath(text_path, QColor("#FFFFFF"))
        for x, y, _vx, _vy, rot, _vr, ci, shape in self.bits:     # 색종이
            p.save()
            p.translate(x, y)
            p.rotate(rot)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(CONFETTI[int(ci)]))
            if shape == 0:
                p.drawRect(QRectF(-5, -3, 10, 6))
            elif shape == 1:
                p.drawEllipse(QPointF(0, 0), 3.5, 3.5)
            else:
                star = QPainterPath()
                for i in range(10):
                    r = 6 if i % 2 == 0 else 2.6
                    a = math.pi / 5 * i
                    pt = QPointF(math.sin(a) * r, -math.cos(a) * r)
                    star.moveTo(pt) if i == 0 else star.lineTo(pt)
                star.closeSubpath()
                p.drawPath(star)
            p.restore()
        p.end()
