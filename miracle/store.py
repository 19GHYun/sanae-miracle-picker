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
DEFAULT_LISTS: dict[str, str] = {}      # 내 목록 (기본 예시는 presets.py — 언어마다)


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
    list_name: str = ""
    text: str = ""
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
    sound_on: bool = True
    sound_level: int = 1
    background: str = "sky"
    hotkey: str = "off"
    obs_text: bool = False
    gacha_pulls: int = 10
    gacha_guarantee: bool = True
    lang: str = "auto"
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
        self.fresh = not (self.root / "settings.json").exists()     # 처음 켬
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
        from .core import mode_name, seed_text, summary
        from .i18n import T
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow([T("시각"), T("종류"), T("목록"), T("항목 수"), T("시드"), T("목록 지문"), T("결과")])
            for d in self.history:
                w.writerow([d.when, mode_name(d.mode), d.title, d.count,
                            seed_text(d.seed), d.print_, summary(d.mode, d.result)])

    # ── 설정 ──
    def save_settings(self) -> None:
        _write(self.root / "settings.json", asdict(self.settings))


def now_text() -> str:
    return datetime.now().isoformat(timespec="seconds")
