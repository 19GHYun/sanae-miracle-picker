# 그림 프롬프트

지금(v0.1) 사나에 그림은 Hokora 에서 쓰던 사나에 스프라이트입니다 (`miracle/sprites/sanae/`).
아래는 추첨기 연출을 더 풍성하게 할 새 그림들입니다. 기준 그림으로 `miracle/sprites/sanae/idle_0.png` 를 첨부합니다.

## 사나에 추첨 연출 시트 (8장, 자홍 배경)

사나에 머리가 초록이라 배경은 자홍입니다.

```
Using the attached image as the exact character and style reference, create ONE sprite sheet
of this same character. Keep the character identical in every frame: same face, same outfit,
same colors, same thick outline, same chibi plush proportions, same size and scale.
The head must stay the same size in every frame. Every frame is full body, facing slightly to
the viewer's right, standing on the same bottom line of its row, with clear magenta space
between frames so that no two frames touch or overlap. Read order: left to right, top to bottom.

Layout: 2 rows x 4 columns, 8 frames.
Row 1: 1. Raising her gohei (white paper wand) high overhead with both hands, a small swirl of wind around it.
2. Swinging the gohei in a big arc to the side, paper streamers flying, a bigger swirl of wind.
3. Pointing the gohei forward dramatically, a sparkle at its tip ("miracle!").
4. Both arms spread wide in a triumphant pose, eyes sparkling, a few small stars around her.
Row 2: 5. Clapping her hands happily with eyes closed in ^^ shape.
6. Holding a small red-and-white ribbon prize envelope out toward the viewer with a big smile.
7. Sheepish: scratching her cheek with one finger, an embarrassed smile and a small sweat drop.
8. Disappointed but cute: shoulders dropped, small sigh puff, eyes half-closed.

Background: solid flat pure magenta (#FF00FF) everywhere. No grid lines, no borders,
no numbers, no text, no shadows.
```

```
python tools/import_sheet.py 사나에추첨.png sanae --names cast_0,cast_1,cast_2,miracle,clap,prize,oops,sigh --append
```

## 스와코 · 카나코 (카메오, 기준 그림 → 4장 시트)

희귀 결과(1등 · 가챠 SSR)일 때 잠깐 나오는 신님들입니다. 먼저 기준 그림을 뽑고, 그 그림을 첨부해서 4장 시트를 뽑습니다.

### 기준 그림

```
The attached image is ONLY a style reference. Copy its art style exactly: chibi plush doll
proportions (very big round head, small bean-shaped body, stubby arms, round nub feet),
thick soft dark-brown outline, big sparkly eyes, cat-like mouth, soft pink blush, flat colors
with gentle shading. Do NOT copy the reference character's hair, bow, or outfit.

Draw this character instead, standing still, full body, body turned slightly to the viewer's right,
arms relaxed, feet at the bottom, centered, portrait canvas 5:6:
[캐릭터 설명]

Background: solid flat pure [BG]. No shadow, no text, no other objects.
```

- 스와코 (`green (#00FF00)`): `Moriya Suwako from Touhou Project: short blonde bob hair, yellow-orange eyes, a big wide-brimmed purple-blue hat with two round frog eyes on top, a purple-blue vest dress with a white shirt and long white sleeves, white thigh-high socks with small frog patterns, brown shoes.`
- 카나코 (`green (#00FF00)`): `Yasaka Kanako from Touhou Project: shoulder-length purple-blue hair, red eyes, a red long-sleeved top with white cuffs and a mirror ornament on her chest, a dark red long skirt, a small rope ring (shimenawa) decoration floating behind her back close to her body, a small maple-leaf hair ornament, brown shoes.`

### 4장 시트

```
Using the attached image as the exact character and style reference, create ONE sprite sheet
of this same character. Keep the character identical in every frame: same face, same outfit,
same colors, same thick outline, same chibi plush proportions, same size and scale.
Every frame is full body, facing slightly to the viewer's right, standing on the same bottom line,
with clear green space between frames so that no two frames touch or overlap.

Layout: 1 row x 4 columns, 4 frames.
1. Standing still with a calm smile. 2. Same with eyes closed (blink).
3. Giving a thumbs-up with a proud grin. 4. Cheering with both arms raised, eyes closed in ^^ shape.

Background: solid flat pure green (#00FF00) everywhere. No grid lines, no borders,
no numbers, no text, no shadows.
```

```
python tools/import_sheet.py 스와코.png suwako --names idle_0,blink,thumbs,cheer
python tools/import_sheet.py 카나코.png kanako --names idle_0,blink,thumbs,cheer
```

## 앱 아이콘 (정사각형 1장)

```
Using the attached image ONLY as an art style reference (thick soft dark-brown outline, flat colors,
cute chibi style), draw a square app icon: the face and shoulders of the same green-haired shrine maiden
(frog hair clip, white snake hair ornament) winking and holding up a white paper gohei wand,
in front of a simple roulette wheel with green, blue and yellow slices, inside a rounded square
with a green-to-blue gradient background. Centered, bold and readable even when small.
No text, no letters, no watermark.
```

> `tools/import_sheet.py` 는 Hokora 저장소의 도구입니다. 필요해지면 이 저장소로 옮겨 옵니다.
