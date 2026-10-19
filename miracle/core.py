# -*- coding: utf-8 -*-
"""추첨 로직 (화면과 분리).

모든 추첨은 시드 하나로 정해진다 → 같은 목록·같은 시드면 언제 다시 해도 같은 결과 (공정성 확인).
시드는 매번 운영체제의 안전한 난수(secrets)로 새로 만든다.
"""
from __future__ import annotations

import hashlib
import random
import re
import secrets
from dataclasses import dataclass

MAX_WEIGHT = 1000
# "이름 x3" · "이름*3" · "치킨x3"(한글 바로 뒤) — "FX3" 같은 영문 이름은 그대로 이름
_WEIGHT = re.compile(r"^(.*?)(?:\s+[xX×]|(?<=[^\x00-\x7F])[xX×]|\s*\*)\s*(\d+)$")


@dataclass(frozen=True)
class Entry:
    name: str
    weight: int = 1


@dataclass(frozen=True)
class Tier:
    name: str
    count: int


def parse(text: str) -> list[Entry]:
    """목록 글 → 항목들.

    - 한 줄에 하나. 빈 줄과 # 로 시작하는 줄은 건너뜀.
    - 엑셀에서 붙여 넣은 줄(탭으로 나뉨)은 칸마다 하나.
    - 한 줄만 있고 쉼표가 있으면 쉼표로 나눔 ("짜장, 짬뽕, 볶음밥").
    - "이름 x3" / "이름*3" / "이름 ×3" 은 가중치(응모권) 3. x0 이면 뺌.
    """
    lines = [ln.strip() for ln in text.replace("\r", "").split("\n")]
    lines = [ln for ln in lines if ln and not ln.startswith("#")]
    if len(lines) == 1 and "," in lines[0]:
        lines = [part.strip() for part in lines[0].split(",")]
    cells = [c.strip() for ln in lines for c in ln.split("\t")]
    out: list[Entry] = []
    for cell in cells:
        if not cell:
            continue
        m = _WEIGHT.match(cell)
        name, weight = (m.group(1).strip(), int(m.group(2))) if m and m.group(1).strip() else (cell, 1)
        if weight <= 0:
            continue
        out.append(Entry(name, min(weight, MAX_WEIGHT)))
    return out


def total_weight(entries: list[Entry]) -> int:
    return sum(e.weight for e in entries)


def new_seed() -> int:
    return secrets.randbits(48)


def seed_text(seed: int) -> str:
    return f"#{seed:012X}"


def fingerprint(entries: list[Entry]) -> str:
    """목록 지문 (같은 목록이었는지 확인용, 앞 8자리)."""
    data = "\n".join(f"{e.name}\t{e.weight}" for e in entries)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()[:8]


def _pick(rng: random.Random, weights: list[int]) -> int:
    r = rng.randrange(sum(weights))
    for i, w in enumerate(weights):
        r -= w
        if r < 0:
            return i
    return len(weights) - 1


def spin(entries: list[Entry], seed: int) -> tuple[int, float]:
    """룰렛: (당첨 칸 번호, 칸 안에서 멈출 위치 0~1). 칸 넓이 = 가중치."""
    if not entries:
        raise ValueError("빈 목록")
    rng = random.Random(seed)
    idx = _pick(rng, [e.weight for e in entries])
    return idx, rng.uniform(0.12, 0.88)


def raffle(entries: list[Entry], tiers: list[Tier], seed: int, unique: bool = True,
           exclude: frozenset[str] | set[str] = frozenset()) -> list[tuple[str, list[str]]]:
    """당첨자 뽑기: 등수 순서대로(첫 등수부터) 뽑음. 가중치 = 응모권 수.

    unique 면 한 사람(이름)은 한 번만 당첨 (같은 이름이 여러 줄이어도). exclude 의 이름은 빼고 뽑음.
    사람이 모자라면 그 등수는 있는 만큼만.
    """
    rng = random.Random(seed)
    pool = [(e.name, e.weight) for e in entries if e.name not in exclude]
    results: list[tuple[str, list[str]]] = []
    for tier in tiers:
        winners: list[str] = []
        for _ in range(max(0, tier.count)):
            if not pool:
                break
            i = _pick(rng, [w for _, w in pool])
            name = pool[i][0]
            winners.append(name)
            if unique:
                pool = [(n, w) for n, w in pool if n != name]
        results.append((tier.name, winners))
    return results


def reveal_order(results: list[tuple[str, list[str]]]) -> list[tuple[str, str]]:
    """발표 순서: 낮은 등수부터 (마지막 등수 → 첫 등수), 등수 안에서는 뽑힌 순서대로."""
    return [(tier, name) for tier, names in reversed(results) for name in names]


def summary(mode: str, result) -> str:
    if mode == "wheel":
        return str(result[0]) if result else "-"
    parts = [f"{tier} {', '.join(names) if names else '없음'}" for tier, names in result]
    return " / ".join(parts)
