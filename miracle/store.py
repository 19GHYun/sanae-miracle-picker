# -*- coding: utf-8 -*-
"""저장: %APPDATA%\\SanaeMiracle 에 목록·기록·설정 (JSON, 원자적으로 저장)."""
from __future__ import annotations

import csv
import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

log = logging.getLogger("Miracle.store")
APP_DIR = "SanaeMiracle"
MAX_HISTORY = 500
DEFAULT_LISTS = {
    "점심 메뉴": "김치찌개\n된장찌개\n돈가스\n짜장면\n짬뽕\n제육볶음\n비빔밥\n라멘\n초밥\n햄버거\n쌀국수\n떡볶이",
    "예시: 가중치": "# '이름 x3' 은 세 배로 잘 뽑혀요\n치킨 x3\n피자 x2\n족발\n보쌈",
}


def data_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home() / ".local" / "share")
    return Path(base) / APP_DIR


@dataclass
class Draw:
    """추첨 한 번의 기록."""
    when: str
    mode: str                 # wheel / raffle
    title: str                # 목록 이름
    count: int                # 항목 수
    seed: int
    print_: str               # 목록 지문
    result: list
    text: str = ""            # 그때의 목록 글 (다시 확인용)


@dataclass
class Settings:
    mode: str = "wheel"
    list_name: str = "점심 메뉴"
    text: str = DEFAULT_LISTS["점심 메뉴"]
    remove_winner: bool = False
    unique: bool = True
    exclude_last: bool = False
    auto_reveal: bool = False
    tiers: list = field(default_factory=lambda: [["당첨", 3]])
    ladder_results: str = "당첨"
    teams_count: int = 2
    teams_style: str = "number"
    dice_kind: str = "dice"
    dice_count: int = 1
    dice_sides: int = 6
    num_lo: int = 1
    num_hi: int = 100
    num_unique: bool = True
    geometry: str = ""


def _read(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    except (OSError, ValueError):
        log.warning("읽기 실패: %s", path, exc_info=True)
        return default


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


class Store:
    def __init__(self, root: Path | None = None):
        self.root = root or data_dir()
        self.lists: dict[str, str] = _read(self.root / "lists.json", None) or dict(DEFAULT_LISTS)
        raw = _read(self.root / "history.json", [])
        self.history: list[Draw] = []
        for d in raw:
            try:
                self.history.append(Draw(**d))
            except TypeError:
                continue
        s = _read(self.root / "settings.json", {})
        known = {k: v for k, v in s.items() if k in Settings.__dataclass_fields__}
        self.settings = Settings(**known)

    # ── 목록 ──
    def save_list(self, name: str, text: str) -> None:
        self.lists[name] = text
        _write(self.root / "lists.json", self.lists)

    def delete_list(self, name: str) -> None:
        self.lists.pop(name, None)
        _write(self.root / "lists.json", self.lists)

    # ── 기록 ──
    def add(self, draw: Draw) -> None:
        self.history.insert(0, draw)
        del self.history[MAX_HISTORY:]
        _write(self.root / "history.json", [asdict(d) for d in self.history])

    def clear_history(self) -> None:
        self.history = []
        _write(self.root / "history.json", [])

    def export_csv(self, path: Path) -> None:
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["시각", "종류", "목록", "항목 수", "시드", "목록 지문", "결과"])
            for d in self.history:
                from .core import MODE_NAMES, seed_text, summary
                w.writerow([d.when, MODE_NAMES.get(d.mode, d.mode), d.title, d.count,
                            seed_text(d.seed), d.print_, summary(d.mode, d.result)])

    # ── 설정 ──
    def save_settings(self) -> None:
        _write(self.root / "settings.json", asdict(self.settings))


def now_text() -> str:
    return datetime.now().isoformat(timespec="seconds")
