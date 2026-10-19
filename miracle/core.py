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

from .i18n import T

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


# ── 순서 정하기 · 팀 나누기 · 사다리 · 주사위 (가중치는 쓰지 않음: 한 줄 = 한 명) ──
TEAM_NAMES = {                                         # 원문(한국어) — 화면에 낼 때 T() 로 번역
    "number": [],                                      # 1팀, 2팀 …
    "touhou": ["하쿠레이", "모리야", "홍마관", "영원정", "백옥루", "지령전", "명련사", "신령묘",
               "요괴의 산", "마법의 숲", "인간 마을", "휘침성"],
    "color": ["빨강", "파랑", "초록", "노랑", "보라", "주황", "하늘", "분홍", "하양", "검정", "회색", "갈색"],
}
LADDER_MAX = 20
DICE_SIDES = (4, 6, 8, 10, 12, 20, 100)
_DICE = re.compile(r"\d+d\d+$")


def names_of(entries: list[Entry]) -> list[str]:
    return [e.name for e in entries]


def order(entries: list[Entry], seed: int) -> list[str]:
    """순서 정하기: 섞은 순서 (1번부터)."""
    names = names_of(entries)
    random.Random(seed).shuffle(names)
    return names


def team_names(n: int, style: str = "number") -> list[str]:
    pool = TEAM_NAMES.get(style) or []
    return [T("{name} 팀", name=T(pool[i])) if i < len(pool) else T("{n}팀", n=i + 1) for i in range(n)]


def teams(entries: list[Entry], n: int, seed: int, style: str = "number") -> list[tuple[str, list[str]]]:
    """팀 나누기: 섞어서 차례로 나눠 줌 → 팀 인원 차이는 많아야 1명. (세력·색 이름이면 이름도 섞임)"""
    rng = random.Random(seed)
    names = names_of(entries)
    rng.shuffle(names)
    n = max(1, min(n, len(names) or 1))
    labels = team_names(n, style)
    if style != "number":
        rng.shuffle(labels)
    out: list[tuple[str, list[str]]] = [(label, []) for label in labels]
    for i, name in enumerate(names):
        out[i % n][1].append(name)
    return out


@dataclass(frozen=True)
class Ladder:
    n: int
    rows: int
    rungs: tuple[tuple[int, int], ...]     # (줄 번호, 왼쪽 세로줄 번호) — 그 줄에서 c 와 c+1 을 잇는 가로줄

    def trace(self, start: int) -> list[tuple[int, int]]:
        """start 세로줄에서 내려가는 길: [(줄, 세로줄)] — 가로줄을 만나면 옆으로 건너감."""
        at = set(self.rungs)
        col, path = start, [(-1, start)]
        for r in range(self.rows):
            if (r, col) in at:
                path.append((r, col))
                col += 1
            elif (r, col - 1) in at:
                path.append((r, col))
                col -= 1
            path.append((r, col))
        path.append((self.rows, col))
        return path

    def end_of(self, start: int) -> int:
        return self.trace(start)[-1][1]


def ladder(n: int, seed: int, rows: int = 0) -> Ladder:
    """사다리: 줄마다 이웃한 가로줄이 붙지 않게 무작위로 놓고, 가로줄이 하나도 없는 칸은 없게."""
    rng = random.Random(seed)
    rows = rows or max(8, min(16, n * 2 + 4))
    rungs: list[tuple[int, int]] = []
    for r in range(rows):
        c = 0
        while c < n - 1:
            if rng.random() < 0.42:
                rungs.append((r, c))
                c += 2                                # 같은 줄 바로 옆 칸엔 안 놓음
            else:
                c += 1
    for _ in range(3):                                # 가로줄이 하나도 없는 칸엔 하나씩 (자리가 없으면 옆을 비켜서)
        for c in range(n - 1):
            if any(cc == c for _, cc in rungs):
                continue
            free = [r for r in range(rows) if (r, c - 1) not in rungs and (r, c + 1) not in rungs]
            r = rng.choice(free) if free else rng.randrange(rows)
            rungs = [(rr, cc) for rr, cc in rungs if not (rr == r and cc in (c - 1, c + 1))]
            rungs.append((r, c))
    return Ladder(n, rows, tuple(sorted(set(rungs))))


def ladder_results(results_text: str, n: int) -> list[str]:
    """사다리 아래 칸: 적은 결과를 n 칸에 맞춤 (모자라면 '꽝', 넘치면 자름). 비어 있으면 당첨 1 + 꽝."""
    got = [e.name for e in parse(results_text)][:n]
    if not got:
        got = [T("당첨")]
    return got + [T("꽝")] * (n - len(got))


def roll(kind: str, seed: int, count: int = 1, sides: int = 6, lo: int = 1, hi: int = 100,
         unique: bool = False) -> list:
    """주사위(dice) / 동전(coin) / 숫자(number)."""
    rng = random.Random(seed)
    count = max(1, count)
    if kind == "coin":
        return [rng.choice([T("앞"), T("뒤")]) for _ in range(count)]
    if kind == "number":
        lo, hi = min(lo, hi), max(lo, hi)
        if unique:
            return rng.sample(range(lo, hi + 1), min(count, hi - lo + 1))
        return [rng.randint(lo, hi) for _ in range(count)]
    return [rng.randint(1, sides) for _ in range(count)]


def dice_label(kind: str, count: int, sides: int, lo: int, hi: int) -> str:
    if kind == "coin":
        return T("동전 {count}개", count=count)
    if kind == "number":
        return T("숫자 {lo}~{hi} · {count}개", lo=min(lo, hi), hi=max(lo, hi), count=count)
    return T("주사위 {count}d{sides}", count=count, sides=sides)


# ── 가챠: [등급 확률] 줄 아래에 그 등급의 항목들. 확률을 안 적은 등급은 남은 확률을 나눠 가짐 ──
_HEADER = re.compile(r"^\[\s*([^\]\s]+)\s*(?:([\d.]+)\s*%?)?\s*\]$")


@dataclass(frozen=True)
class Rarity:
    name: str
    rate: float                 # % (합이 100 이 되게 맞춤)
    items: tuple[str, ...]


def parse_pool(text: str) -> list[Rarity]:
    """가챠 목록: 위에 적은 등급일수록 귀함. 등급 줄이 없으면 전부 한 등급(N)."""
    groups: list[list] = []
    for raw in text.replace("\r", "").split("\n"):
        ln = raw.strip()
        if not ln or ln.startswith("#"):
            continue
        m = _HEADER.match(ln)
        if m:
            groups.append([m.group(1), float(m.group(2)) if m.group(2) else None, []])
        else:
            if not groups:
                groups.append(["N", None, []])
            groups[-1][2].append(ln)
    groups = [g for g in groups if g[2]]
    given = sum(g[1] for g in groups if g[1] is not None)
    blank = [g for g in groups if g[1] is None]
    for g in blank:
        g[1] = max(0.0, 100.0 - given) / len(blank) if given < 100 else 0.0
    total = sum(g[1] for g in groups) or 1.0
    if all(g[1] == 0 for g in groups):
        total = len(groups) or 1
        for g in groups:
            g[1] = 1.0
    return [Rarity(name, rate * 100.0 / total, tuple(items)) for name, rate, items in groups]


def gacha(pool: list[Rarity], n: int, seed: int, guarantee: bool = True) -> list[tuple[str, str]]:
    """n 번 뽑기 → [(등급, 항목)]. guarantee: 10연 이상에서 다 가장 흔한 등급이면 마지막 장은 그보다 위 등급."""
    rng = random.Random(seed)
    out: list[tuple[str, str]] = []
    for i in range(max(1, n)):
        cand = pool
        if (guarantee and n >= 10 and i == n - 1 and len(pool) > 1
                and all(r == pool[-1].name for r, _ in out)):
            cand = pool[:-1]
        weights = [r.rate for r in cand]
        x = rng.random() * (sum(weights) or 1.0)
        pick = cand[-1]
        for r, w in zip(cand, weights):
            x -= w
            if x < 0:
                pick = r
                break
        out.append((pick.name, rng.choice(pick.items)))
    return out


def pool_entries(pool: list[Rarity]) -> list[Entry]:
    """기록용: 가챠 목록을 지문을 낼 수 있는 항목들로."""
    return [Entry(f"{r.name}:{r.rate:.4f}:{item}") for r in pool for item in r.items]


MODE_NAMES = {"wheel": "룰렛", "raffle": "당첨자 뽑기", "ladder": "사다리", "teams": "팀 나누기",
              "order": "순서 정하기", "dice": "주사위", "gacha": "가챠"}       # 원문 (로그용) — 화면엔 mode_name
BLANKS = {"꽝", "통과", "패스", "はずれ", "ハズレ", "パス", "スルー", "miss", "pass", "none", "-", ""}


def mode_name(mode: str) -> str:
    return T(MODE_NAMES[mode]) if mode in MODE_NAMES else mode


def is_blank(result: str) -> bool:
    """사다리 결과가 꽝 같은 것인지 (어느 언어로 적어도)."""
    s = result.strip()
    return s.lower() in BLANKS or s == T("꽝")


def headline(mode: str, result) -> str:
    """한 줄 결과 (OBS winner.txt 등)."""
    if mode == "wheel":
        return str(result[0]) if result else ""
    if mode == "raffle":
        for tier, names in result:
            if names:
                return f"{tier}: {', '.join(names)}"
        return T("당첨자 없음")
    if mode == "ladder":
        hits = [f"{a} → {b}" for a, b in result if not is_blank(b)]
        return ", ".join(hits) if hits else T("모두 꽝!")
    if mode == "teams":
        return " / ".join(f"{t}: {', '.join(m)}" for t, m in result)
    if mode == "order":
        return T("1번: {name}", name=result[0]) if result else ""
    if mode == "gacha":
        ranks, pulls = result
        for r in ranks:
            got = [item for rr, item in pulls if rr == r]
            if got:
                return f"{r}: {', '.join(got)}"
        return ""
    return summary(mode, result)


def summary(mode: str, result) -> str:
    if mode == "wheel":
        return str(result[0]) if result else "-"
    if mode == "order":
        return " → ".join(f"{i + 1}.{n}" for i, n in enumerate(result))
    if mode == "gacha":                                  # result = [등급 순서, [[등급, 항목], …]]
        ranks, pulls = result
        parts = []
        for r in ranks:
            got = [item for rr, item in pulls if rr == r]
            if got:
                parts.append(f"{r} " + (", ".join(got) if len(got) <= 3 else f"×{len(got)}"))
        return " · ".join(parts)
    if mode == "ladder":
        return ", ".join(f"{a}→{b}" for a, b in result)
    if mode == "dice":
        label, values = result[0], result[1]
        text = ", ".join(str(v) for v in values)
        if _DICE.search(label) and len(values) > 1:                  # "주사위 2d6" 처럼 (어느 언어든)
            text += T(" (합 {total})", total=sum(values))
        return f"{label}: {text}"
    parts = [f"{tier} {', '.join(names) if names else T('없음')}" for tier, names in result]
    return " / ".join(parts)
