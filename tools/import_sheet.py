# -*- coding: utf-8 -*-
"""
AI 로 뽑은 초록(또는 자홍) 배경 스프라이트 시트 → 무대용 캐릭터 그림. (Hokora 의 같은 도구를 이 저장소에 맞춘 것)

  python tools/import_sheet.py 시트.png suwako                       (이름 없이: 번호가 붙은 미리보기만)
  python tools/import_sheet.py 시트.png suwako --names idle_0,blink,thumbs,cheer
  python tools/import_sheet.py 시트.png sanae --append --ref oops --names cast_0,cast_1,...   (기존 그림에 추가)
  이름 자리에 - 를 쓰면 그 장면은 버림 (예: idle_0,-,cheer)

하는 일
  1. 오른쪽 아래의 반투명 흰 ✦(Gemini 표시)를 배경색으로 (가까이 있는 캐릭터는 그대로)
  2. 초록 배경(#00FF00) · 자홍 배경(#FF00FF)을 투명하게, 가장자리의 색 번짐 제거
  3. 배경 사이에 떨어져 있는 캐릭터를 하나씩 찾아 읽는 순서(위→아래, 왼→오)로 번호 매기기
  4. 모든 그림을 같은 비율로 줄이고(기준 그림의 키 = STANDING_PX), 그림마다 발 위치를 manifest.json 에
     → miracle/sprites/<캐릭터>/<이름>.png + manifest.json, 미리보기는 build/<캐릭터>_preview.png (exe 에 안 들어가게)

프레임 이름: <동작> 한 장, 또는 <동작>_0, <동작>_1 … 여러 장(차례로 재생)
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import deque
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter

ROOT = Path(__file__).resolve().parent.parent
SPRITES = ROOT / "miracle" / "sprites"
STANDING_PX = 200      # 저장할 때 기준 그림(서 있는 자세)의 키
PAD = 6
GRID = 4               # 캐릭터 찾기는 1/4 크기 격자로 (속도)
_qt_app = None


def key_color(img: QImage) -> str:
    """배경색 자동 판별: 그림 테두리 픽셀 평균이 초록이면 "green", 자홍이면 "magenta"."""
    w, h = img.width(), img.height()
    pts = [(x, y) for x in range(0, w, max(1, w // 40)) for y in (0, h - 1)]
    pts += [(x, y) for y in range(0, h, max(1, h // 40)) for x in (0, w - 1)]
    r = g = b = 0
    for x, y in pts:
        c = img.pixel(x, y)
        r, g, b = r + ((c >> 16) & 255), g + ((c >> 8) & 255), b + (c & 255)
    return "magenta" if min(r, b) > g else "green"


def remove_corner_star(src: QImage) -> QImage:
    """오른쪽 아래의 반투명 흰 ✦ → 배경색. '배경 위에 흰빛이 얹힌' 픽셀 중 가장 큰 덩어리(= 별)만 바꿔서,
    가까이 있는 캐릭터의 흰 옷 가장자리는 건드리지 않는다. 자리 · 크기는 그림마다 찾음."""
    img = src.convertToFormat(QImage.Format_ARGB32)
    w, h = img.width(), img.height()
    magenta = key_color(img) == "magenta"
    data = bytearray(bytes(img.constBits()))
    st = img.bytesPerLine()
    box = max(200, min(w, h) // 5)
    hits = set()
    for y in range(h - box, h):
        for x in range(w - box, w):
            i = y * st + x * 4
            b, g, r = data[i], data[i + 1], data[i + 2]
            if magenta:            # 자홍 + 흰빛 = (255, 255·α, 255)
                star = r > 230 and b > 230 and abs(r - b) < 25 and 40 < g < 232
            else:                  # 초록 + 흰빛 = (255·α, 255, 255·α)
                star = g > 230 and abs(r - b) < 25 and 40 < r < 232
            if star:
                hits.add((x, y))
    best: list = []
    seen: set = set()
    for start in hits:                                   # 가장 큰 덩어리 = 별
        if start in seen:
            continue
        comp, q = [], deque([start])
        seen.add(start)
        while q:
            x, y = q.popleft()
            comp.append((x, y))
            for nb in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if nb in hits and nb not in seen:
                    seen.add(nb)
                    q.append(nb)
        if len(comp) > len(best):
            best = comp
    if len(best) < 150:
        return src
    xs, ys = [p[0] for p in best], [p[1] for p in best]
    print(f"✦ 표시 지움: ({min(xs)}, {min(ys)}) ~ ({max(xs)}, {max(ys)}), {len(best)}픽셀")
    bg = (255, 0, 255) if magenta else (0, 255, 0)
    for x, y in best:
        i = y * st + x * 4
        data[i], data[i + 1], data[i + 2] = bg[2], bg[1], bg[0]
    return QImage(bytes(data), w, h, st, QImage.Format_ARGB32).copy()


def chroma_key(src: QImage, key: str | None = None) -> QImage:
    """초록(또는 자홍) 배경을 투명하게. 캐릭터 안의 같은 계열 색은 남긴다.

    1. 그림 가장자리에서 이어진 '배경 계열' 픽셀만 배경으로 (윤곽선 안쪽의 옷 · 리본은 닿지 않음)
    2. 윤곽선에 갇힌 배경 틈(팔과 몸 사이 등)은 배경색과 거의 같은 '순수한 배경색'만 추가로 배경 처리
    3. 배경 바로 옆 픽셀만 색 번짐을 눌러줌 (안쪽 색은 건드리지 않음)
    초록 머리(사나에)는 자홍 배경으로 뽑으면 된다.
    """
    src = src.convertToFormat(QImage.Format_ARGB32)
    key = key or key_color(src)
    magenta = key == "magenta"
    w, h = src.width(), src.height()
    n = w * h
    data = bytearray(bytes(src.constBits()))  # BGRA
    spill = bytearray(n)       # 배경색 성분이 나머지보다 얼마나 센지 (0~255)
    loose = bytearray(n)       # 배경이거나 배경과 섞인 가장자리일 수 있음
    bg = bytearray(n)
    for k in range(n):
        i = k * 4
        b, g, r = data[i], data[i + 1], data[i + 2]
        if magenta:                # 자홍: r · b 가 함께 세고 g 가 약함
            on, off = (r if r < b else b), g
            pure = r > 170 and b > 170 and g < 110
        else:                      # 초록: g 가 세고 r · b 가 약함
            on, off = g, (r if r > b else b)
            pure = g > 170 and r < 110 and b < 110
        sv = on - off
        if sv > 0:
            spill[k] = sv
            if on > 100 and sv > 60:
                loose[k] = 1
                if pure and sv > 120:
                    bg[k] = 1          # 순수한 배경색 → 갇힌 틈이어도 배경
    q = deque(k for k in list(range(w)) + list(range(n - w, n)) + list(range(0, n, w)) + list(range(w - 1, n, w))
              if loose[k])
    for k in q:
        bg[k] = 3
    while q:
        k = q.popleft()
        x = k % w
        for nk in (k - w, k + w, k - 1 if x else -1, k + 1 if x < w - 1 else -1):
            if 0 <= nk < n and loose[nk] and not (bg[nk] & 2):
                bg[nk] = 3             # 1 = 배경, 2 = 방문함
                q.append(nk)

    def despill(i: int, amount: int) -> None:
        if amount <= 0:
            return
        if magenta:
            data[i] -= min(amount, data[i])            # b
            data[i + 2] -= min(amount, data[i + 2])    # r
        else:
            data[i + 1] -= min(amount, data[i + 1])    # g

    for k in range(n):
        sv = spill[k]
        if bg[k]:
            i = k * 4
            data[i + 3] = max(0, 255 - min(255, sv * 3))
            despill(i, sv)
        elif sv > 20:
            x = k % w
            if ((k >= w and bg[k - w]) or (k + w < n and bg[k + w])
                    or (x and bg[k - 1]) or (x < w - 1 and bg[k + 1])):
                despill(k * 4, sv - 20)
    return QImage(bytes(data), w, h, QImage.Format_ARGB32).copy()


def find_blobs(img: QImage):
    """불투명한 덩어리(캐릭터)들을 읽는 순서로: ([(경계 상자 (x0, y0, x1, y1), 라벨)...], 격자 라벨 배열, 격자 폭).
    작은 조각(떨어진 반짝이 · 바람 · 땀방울)은 가장 가까운 캐릭터에 합친다."""
    w, h = img.width(), img.height()
    gw, gh = (w + GRID - 1) // GRID, (h + GRID - 1) // GRID
    data = bytes(img.constBits())
    stride = img.bytesPerLine()
    solid = bytearray(gw * gh)
    for gy in range(gh):
        y = min(h - 1, gy * GRID + GRID // 2)
        row = y * stride
        for gx in range(gw):
            x = min(w - 1, gx * GRID + GRID // 2)
            if data[row + x * 4 + 3] > 60:
                solid[gy * gw + gx] = 1
    labels = [0] * (gw * gh)
    comps = []  # [x0, y0, x1, y1, 넓이, 라벨]
    for start in range(gw * gh):
        if not solid[start] or labels[start]:
            continue
        lab = len(comps) + 1
        q = deque([start])
        labels[start] = lab
        x0 = y0 = 10 ** 9
        x1 = y1 = area = 0
        while q:
            c = q.popleft()
            cy, cx = divmod(c, gw)
            area += 1
            x0, x1, y0, y1 = min(x0, cx), max(x1, cx), min(y0, cy), max(y1, cy)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < gw and 0 <= ny < gh:
                    nb = ny * gw + nx
                    if solid[nb] and not labels[nb]:
                        labels[nb] = lab
                        q.append(nb)
        comps.append([x0, y0, x1, y1, area, lab])
    if not comps:
        return [], labels, gw
    big = max(c[4] for c in comps)
    main = [c for c in comps if c[4] >= big * 0.05]
    remap = {}
    for c in comps:
        if c in main:
            continue
        cx, cy = (c[0] + c[2]) / 2, (c[1] + c[3]) / 2
        tgt = min(main, key=lambda m: max(0, m[0] - cx, cx - m[2]) + max(0, m[1] - cy, cy - m[3]))
        tgt[0], tgt[1] = min(tgt[0], c[0]), min(tgt[1], c[1])
        tgt[2], tgt[3] = max(tgt[2], c[2]), max(tgt[3], c[3])
        remap[c[5]] = tgt[5]
    if remap:
        labels = [remap.get(v, v) for v in labels]
    blobs = [((c[0] * GRID, c[1] * GRID, min(w, (c[2] + 1) * GRID), min(h, (c[3] + 1) * GRID)), c[5])
             for c in main]
    cy_of = lambda b: (b[0][1] + b[0][3]) / 2  # noqa: E731
    med_h = sorted(b[0][3] - b[0][1] for b in blobs)[len(blobs) // 2]
    blobs.sort(key=cy_of)
    rows, row = [], [blobs[0]]
    for b in blobs[1:]:
        if cy_of(b) - cy_of(row[0]) > med_h * 0.5:
            rows.append(row)
            row = [b]
        else:
            row.append(b)
    rows.append(row)
    return [b for r in rows for b in sorted(r, key=lambda b: b[0][0])], labels, gw


def tight(img: QImage, blob, labels, gw) -> tuple[QImage, float]:
    """상자 안에서 이 캐릭터 픽셀만 남겨(옆 캐릭터 조각은 지움) 딱 맞게 자르고, 머리 무게중심 x 를 돌려준다
    (몸 전체로 잡으면 팔을 내밀 때마다 중심이 흔들려 보임)."""
    (x0, y0, x1, y1), lab = blob
    crop = img.copy(x0, y0, x1 - x0, y1 - y0).convertToFormat(QImage.Format_ARGB32)
    w, h = crop.width(), crop.height()
    stride = crop.bytesPerLine()
    data = bytearray(bytes(crop.constBits()))
    gh = len(labels) // gw

    def owner_other(px: int, py: int) -> bool:
        gx, gy = (x0 + px) // GRID, (y0 + py) // GRID
        mine = other = False
        for ny in (gy - 1, gy, gy + 1):
            if 0 <= ny < gh:
                for nx in (gx - 1, gx, gx + 1):
                    if 0 <= nx < gw:
                        v = labels[ny * gw + nx]
                        if v == lab:
                            mine = True
                        elif v:
                            other = True
        return other and not mine

    minx, miny, maxx, maxy = w, h, -1, -1
    for y in range(h):
        row = y * stride
        for x in range(w):
            i = row + x * 4 + 3
            if not data[i]:
                continue
            if owner_other(x, y):
                data[i] = 0
                continue
            if data[i] > 60:
                minx, maxx, miny, maxy = min(minx, x), max(maxx, x), min(miny, y), max(maxy, y)
    band0, band1 = miny + int((maxy - miny) * 0.12), miny + int((maxy - miny) * 0.55)
    sx = sa = 0
    for y in range(band0, band1 + 1):
        row = y * stride
        for x in range(minx, maxx + 1):
            a = data[row + x * 4 + 3]
            if a > 60:
                sx += x * a
                sa += a
    clean = QImage(bytes(data), w, h, stride, QImage.Format_ARGB32).copy()
    return clean.copy(minx, miny, maxx - minx + 1, maxy - miny + 1), (sx / max(1, sa)) - minx


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sheet", type=Path)
    ap.add_argument("character", help="캐릭터 키 (sanae, suwako, kanako …)")
    ap.add_argument("--names", help="찾은 순서대로 붙일 프레임 이름, 쉼표로 구분")
    ap.add_argument("--ref", help="크기 기준 그림 이름 — 이 그림의 키가 STANDING_PX 가 됨 (기본: idle_0 / idle)")
    ap.add_argument("--append", action="store_true", help="기존 그림을 지우지 않고 추가 (같은 이름은 덮어씀)")
    args = ap.parse_args()
    global _qt_app
    _qt_app = QGuiApplication.instance() or QGuiApplication(sys.argv)

    src = QImage(str(args.sheet))
    if src.isNull():
        print(f"그림을 읽지 못했습니다: {args.sheet}")
        return 1
    keyed = chroma_key(remove_corner_star(src))
    blobs, labels, gw = find_blobs(keyed)
    print(f"캐릭터 {len(blobs)}개 찾음")
    wanted = [n.strip() for n in args.names.split(",")] if args.names else None
    names = wanted or [f"frame_{i + 1}" for i in range(len(blobs))]
    if len(names) != len(blobs):
        print(f"이름 {len(names)}개와 찾은 캐릭터 {len(blobs)}개의 수가 다릅니다. 미리보기를 보고 다시 지정하세요.")
        names, wanted = [f"frame_{i + 1}" for i in range(len(blobs))], None
    frames = [tight(keyed, b, labels, gw) for b in blobs]
    keep = [i for i, n in enumerate(names) if n != "-"]
    frames, names = [frames[i] for i in keep], [names[i] for i in keep]
    ref = next((names.index(n) for n in (args.ref, "idle_0", "idle") if n and n in names), None)
    scale = STANDING_PX / (frames[ref][0].height() if ref is not None else max(img.height() for img, _ in frames))

    out_dir = SPRITES / args.character
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "manifest.json"
    manifest = {"version": 2, "standing_height": STANDING_PX, "facing": 1, "frames": {}, "sources": []}
    if args.append and manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))     # 다른 항목(walk_cycles 등)은 그대로
    else:
        for old in out_dir.glob("*.png"):
            old.unlink()
    for (img, cx), name in zip(frames, names):           # 그림마다 딱 맞는 캔버스 + 발 위치(머리 중심 x, 바닥 y)
        tw, th = img.width() * scale, img.height() * scale
        ax = int(max(cx * scale, tw - cx * scale)) + PAD
        canvas = QImage(ax * 2, int(th) + PAD * 2, QImage.Format_ARGB32_Premultiplied)
        canvas.fill(Qt.transparent)
        p = QPainter(canvas)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        ay = canvas.height() - PAD
        p.drawImage(QRectF(ax - cx * scale, ay - th, tw, th), img)
        p.end()
        canvas.save(str(out_dir / f"{name}.png"))
        manifest["frames"][name] = [ax, ay]
    if wanted:
        manifest.setdefault("sources", []).append(args.sheet.name)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    _save_preview(out_dir, names, manifest["frames"])
    print(f"저장: {out_dir}")
    if not wanted:
        print(f"미리보기(build/{out_dir.name}_preview.png)를 보고 --names 로 이름을 붙여 다시 실행하세요.")
    return 0


def _save_preview(out_dir: Path, names: list[str], anchors: dict[str, list[float]]) -> None:
    """이번에 넣은 그림들을 같은 바닥선 · 가운데선에 맞춰 번호와 함께 (정렬 확인용)."""
    imgs = [QImage(str(out_dir / f"{n}.png")) for n in names]
    left = max(anchors[n][0] for n in names)
    right = max(img.width() - anchors[n][0] for n, img in zip(names, imgs))
    up = max(anchors[n][1] for n in names)
    down = max(img.height() - anchors[n][1] for n, img in zip(names, imgs))
    cell_w, cell_h = int(left + right) + 10, int(up + down) + 28
    cols = min(6, len(names))
    rows = (len(names) + cols - 1) // cols
    prev = QImage(cell_w * cols, cell_h * rows, QImage.Format_ARGB32)
    prev.fill(QColor("#EDE6EA"))
    p = QPainter(prev)
    p.setFont(QFont("Malgun Gothic", 10))
    for i, (name, img) in enumerate(zip(names, imgs)):
        ox, oy = (i % cols) * cell_w + 5 + left, (i // cols) * cell_h + 4 + up
        p.setPen(QColor(200, 16, 46, 120))
        p.drawLine(QPointF(ox - left, oy), QPointF(ox + right, oy))
        p.drawLine(QPointF(ox, oy - up), QPointF(ox, oy + down))
        ax, ay = anchors[name]
        p.drawImage(QPointF(ox - ax, oy - ay), img)
        p.setPen(QColor("#2B1D21"))
        p.drawText(QRectF(ox - left, oy + down + 2, cell_w - 10, 20), Qt.AlignCenter, f"{i + 1}. {name}")
    p.end()
    (ROOT / "build").mkdir(exist_ok=True)
    prev.save(str(ROOT / "build" / f"{out_dir.name}_preview.png"))


if __name__ == "__main__":
    sys.exit(main())
