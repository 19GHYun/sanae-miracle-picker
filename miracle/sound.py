# -*- coding: utf-8 -*-
"""효과음: 소리 파일 없이 코드로 합성해서 데이터 폴더(sounds/)에 만들어 두고 Windows 기본 재생(winsound)으로 낸다.

winsound 는 한 번에 소리 하나만 낼 수 있어서, 룰렛은 바늘이 칸을 넘는 순간들을 미리 계산해
틱 소리를 한 파일로 만들어 튼다 (spin).
MIRACLE_MUTE=1 이면 소리를 내지 않는다 (시험용) — 그래도 무엇을 냈을지는 played 에 남긴다.
"""
from __future__ import annotations

import logging
import math
import os
import random
import wave
from array import array
from pathlib import Path

try:                                  # 맨 위에서 불러야 exe 에도 확실히 들어감
    import winsound
except ImportError:
    winsound = None

log = logging.getLogger("Miracle.sound")
RATE = 22050
LEVELS = (0.35, 0.6, 0.9)             # 작게 · 보통 · 크게
enabled = True
level = 1
played: list[str] = []                # 낸 소리 (최근 50개, 시험용 기록)
heard: set[str] = set()               # 한 번이라도 낸 소리
_rendered: set[str] = set()


def folder() -> Path:
    from .store import data_dir
    return data_dir() / "sounds"


# ── 합성 도구 ──
def _buf(seconds: float) -> list[float]:
    return [0.0] * int(RATE * seconds)


def _tone(buf: list[float], start: float, freq: float, dur: float, amp: float, decay: float = 6.0,
          partials: tuple = ((1.0, 1.0), (2.0, 0.3), (3.0, 0.12)), attack: float = 0.004) -> None:
    i0 = int(start * RATE)
    n = min(len(buf) - i0, int(dur * RATE))
    a_n = max(1, int(attack * RATE))
    for ratio, a in partials:
        f = freq * ratio
        if f >= RATE / 2:
            continue
        w = 2 * math.pi * f / RATE
        d = decay * (1 + (ratio - 1) * 0.5)
        for j in range(n):
            fall = math.exp(-d * j / RATE)
            if fall < 0.001:                             # 다 잦아들면 끝 (어택 구간의 0 은 빼고 판단)
                break
            buf[i0 + j] += amp * a * fall * min(1.0, (j + 1) / a_n) * math.sin(w * j)


def _glide(buf: list[float], start: float, f0: float, f1: float, dur: float, amp: float) -> None:
    i0 = int(start * RATE)
    n = min(len(buf) - i0, int(dur * RATE))
    phase = 0.0
    for j in range(n):
        u = j / max(1, n)
        phase += 2 * math.pi * (f0 + (f1 - f0) * u) / RATE
        env = math.sin(math.pi * u) ** 0.6
        buf[i0 + j] += amp * env * math.sin(phase)


def _noise(buf: list[float], start: float, dur: float, amp: float, decay: float, rng: random.Random,
           tone: float = 0.0) -> None:
    i0 = int(start * RATE)
    n = min(len(buf) - i0, int(dur * RATE))
    last = 0.0
    for j in range(n):
        env = math.exp(-decay * j / RATE)
        x = rng.uniform(-1, 1)
        last = last * tone + x * (1 - tone)          # tone 이 클수록 부드러운(낮은) 잡음
        buf[i0 + j] += amp * env * last


def _save(name: str, buf: list[float]) -> Path:
    peak = max((abs(x) for x in buf), default=0.0) or 1.0
    k = LEVELS[max(0, min(2, level))] * 32767 / max(peak, 1.0)
    path = folder() / f"{name}_{level}.wav"
    path.parent.mkdir(parents=True, exist_ok=True)
    if winsound is not None and os.environ.get("MIRACLE_MUTE") != "1":
        try:
            winsound.PlaySound(None, 0)                  # 재생 중인 파일을 덮어쓰지 않게 멈춤
        except RuntimeError:
            pass
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(array("h", (int(max(-1.0, min(1.0, x)) * k) for x in buf)).tobytes())
    return path


# ── 소리들 ──
def make(name: str, seconds: float = 1.0, ticks: list[float] | None = None) -> list[float]:
    rng = random.Random(7)
    if name == "fanfare":                               # 도-미-솔-도 + 화음 + 반짝
        b = _buf(1.9)
        for i, f in enumerate((523.25, 659.25, 783.99, 1046.5)):
            _tone(b, i * 0.11, f, 0.5, 0.5, 5.0)
        for f in (1046.5, 1318.5, 1568.0):
            _tone(b, 0.48, f, 1.4, 0.35, 2.6)
        for _ in range(10):
            _tone(b, rng.uniform(0.5, 1.3), rng.uniform(2400, 3600), 0.25, 0.12, 14.0, ((1.0, 1.0),))
        return b
    if name == "ding":
        b = _buf(0.8)
        _tone(b, 0, 1318.5, 0.8, 0.6, 5.0, ((1.0, 1.0), (2.76, 0.25)))
        return b
    if name == "win":                                   # 딩-동 (위로)
        b = _buf(1.0)
        _tone(b, 0, 1046.5, 0.6, 0.5, 5.0, ((1.0, 1.0), (2.76, 0.2)))
        _tone(b, 0.13, 1568.0, 0.85, 0.55, 4.0, ((1.0, 1.0), (2.76, 0.2)))
        return b
    if name == "boop":                                  # 머쓱
        b = _buf(0.35)
        _glide(b, 0, 420, 250, 0.32, 0.6)
        return b
    if name == "pop":
        b = _buf(0.12)
        _glide(b, 0, 600, 1300, 0.08, 0.6)
        return b
    if name == "coin":
        b = _buf(0.7)
        for t in (0.0, 0.07):
            _tone(b, t, 2637, 0.6, 0.45, 6.0, ((1.0, 1.0), (1.5, 0.4), (2.4, 0.2)))
        return b
    if name == "drumroll":                              # 작은북 연타, 점점 세게
        b = _buf(seconds + 0.1)
        t = 0.0
        while t < seconds:
            u = t / max(0.01, seconds)
            _noise(b, t, 0.03, 0.25 + 0.45 * u, 90.0, rng, 0.3)
            t += 0.045 - 0.012 * u
        return b
    if name == "rattle":                                # 주사위 달그락
        b = _buf(seconds + 0.1)
        t = 0.0
        while t < seconds:
            u = t / max(0.01, seconds)
            _noise(b, t, 0.012, 0.6, 260.0, rng, 0.1)
            _tone(b, t, rng.uniform(1800, 2600), 0.03, 0.15, 120.0, ((1.0, 1.0),))
            t += rng.uniform(0.03, 0.07) + 0.12 * u * u
        return b
    if name == "spin":                                  # 룰렛 바늘 틱 (미리 계산한 순간마다)
        b = _buf(seconds + 0.2)
        for t in ticks or []:
            _noise(b, t, 0.006, 0.5, 400.0, rng, 0.2)
            _tone(b, t, 1900, 0.025, 0.25, 160.0, ((1.0, 1.0),))
        return b
    raise ValueError(name)


STATIC = ("fanfare", "ding", "win", "boop", "pop", "coin")


def render(name: str, seconds: float = 1.0, ticks: list[float] | None = None) -> Path:
    """소리 파일을 만들어(이미 있으면 그대로) 경로를 돌려줌. 길이가 바뀌는 소리는 이름에 길이를 붙임."""
    key = name if name in STATIC else f"{name}{int(round(seconds * 10)):03d}"
    path = folder() / f"{key}_{level}.wav"
    if name == "spin" or not path.exists():
        path = _save(key, make(name, seconds, ticks))
    return path


def play(name: str, seconds: float = 1.0, ticks: list[float] | None = None) -> bool:
    """비동기로 재생 (기다리지 않음). 냈으면 True."""
    played.append(name)
    heard.add(name)
    del played[:-50]
    if not enabled or os.environ.get("MIRACLE_MUTE") == "1" or winsound is None:
        return False
    try:
        path = render(name, seconds, ticks)
        winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
        return True
    except (OSError, RuntimeError, ValueError):
        log.warning("효과음 재생 실패: %s", name, exc_info=True)
        return False


def stop() -> None:
    if winsound is not None and os.environ.get("MIRACLE_MUTE") != "1":
        try:
            winsound.PlaySound(None, 0)
        except RuntimeError:
            pass
