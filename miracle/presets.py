# -*- coding: utf-8 -*-
"""기본 목록 (지울 수 없는 예시들): 언어마다. 고쳐서 저장하면 내 목록이 된다."""
from __future__ import annotations

MARK = "📦 "

# (한국어, 日本語, English)
TOUHOU_CHARACTERS = [
    ("하쿠레이 레이무", "博麗霊夢", "Reimu Hakurei"), ("키리사메 마리사", "霧雨魔理沙", "Marisa Kirisame"),
    ("루미아", "ルーミア", "Rumia"), ("대요정", "大妖精", "Daiyousei"), ("치르노", "チルノ", "Cirno"),
    ("홍 메이링", "紅美鈴", "Hong Meiling"), ("코아쿠마", "小悪魔", "Koakuma"),
    ("파츄리 널리지", "パチュリー・ノーレッジ", "Patchouli Knowledge"), ("이자요이 사쿠야", "十六夜咲夜", "Sakuya Izayoi"),
    ("레밀리아 스칼렛", "レミリア・スカーレット", "Remilia Scarlet"), ("플랑드르 스칼렛", "フランドール・スカーレット", "Flandre Scarlet"),
    ("레티 화이트락", "レティ・ホワイトロック", "Letty Whiterock"), ("첸", "橙", "Chen"),
    ("앨리스 마가트로이드", "アリス・マーガトロイド", "Alice Margatroid"), ("릴리 화이트", "リリーホワイト", "Lily White"),
    ("루나사 프리즘리버", "ルナサ・プリズムリバー", "Lunasa Prismriver"), ("메를랑 프리즘리버", "メルラン・プリズムリバー", "Merlin Prismriver"),
    ("리리카 프리즘리버", "リリカ・プリズムリバー", "Lyrica Prismriver"), ("콘파쿠 요우무", "魂魄妖夢", "Youmu Konpaku"),
    ("사이교지 유유코", "西行寺幽々子", "Yuyuko Saigyouji"), ("야쿠모 란", "八雲藍", "Ran Yakumo"),
    ("야쿠모 유카리", "八雲紫", "Yukari Yakumo"), ("이부키 스이카", "伊吹萃香", "Suika Ibuki"),
    ("리글 나이트버그", "リグル・ナイトバグ", "Wriggle Nightbug"), ("미스티아 로렐라이", "ミスティア・ローレライ", "Mystia Lorelei"),
    ("카미시라사와 케이네", "上白沢慧音", "Keine Kamishirasawa"), ("이나바 테위", "因幡てゐ", "Tewi Inaba"),
    ("레이센 우동게인 이나바", "鈴仙・優曇華院・イナバ", "Reisen Udongein Inaba"), ("야고코로 에이린", "八意永琳", "Eirin Yagokoro"),
    ("호라이산 카구야", "蓬莱山輝夜", "Kaguya Houraisan"), ("후지와라노 모코우", "藤原妹紅", "Fujiwara no Mokou"),
    ("샤메이마루 아야", "射命丸文", "Aya Shameimaru"), ("메디슨 멜랑콜리", "メディスン・メランコリー", "Medicine Melancholy"),
    ("카자미 유카", "風見幽香", "Yuuka Kazami"), ("오노즈카 코마치", "小野塚小町", "Komachi Onozuka"),
    ("시키에이키 야마자나두", "四季映姫・ヤマザナドゥ", "Eiki Shiki, Yamaxanadu"), ("아키 시즈하", "秋静葉", "Shizuha Aki"),
    ("아키 미노리코", "秋穣子", "Minoriko Aki"), ("카기야마 히나", "鍵山雛", "Hina Kagiyama"),
    ("카와시로 니토리", "河城にとり", "Nitori Kawashiro"), ("이누바시리 모미지", "犬走椛", "Momiji Inubashiri"),
    ("코치야 사나에", "東風谷早苗", "Sanae Kochiya"), ("야사카 카나코", "八坂神奈子", "Kanako Yasaka"),
    ("모리야 스와코", "洩矢諏訪子", "Suwako Moriya"), ("나가에 이쿠", "永江衣玖", "Iku Nagae"),
    ("히나나위 텐시", "比那名居天子", "Tenshi Hinanawi"), ("키스메", "キスメ", "Kisume"),
    ("쿠로다니 야마메", "黒谷ヤマメ", "Yamame Kurodani"), ("미즈하시 파르시", "水橋パルスィ", "Parsee Mizuhashi"),
    ("호시구마 유기", "星熊勇儀", "Yuugi Hoshiguma"), ("코메이지 사토리", "古明地さとり", "Satori Komeiji"),
    ("카엔뵤 린", "火焔猫燐", "Rin Kaenbyou"), ("레이우지 우츠호", "霊烏路空", "Utsuho Reiuji"),
    ("코메이지 코이시", "古明地こいし", "Koishi Komeiji"), ("나즈린", "ナズーリン", "Nazrin"),
    ("타타라 코가사", "多々良小傘", "Kogasa Tatara"), ("쿠모이 이치린", "雲居一輪", "Ichirin Kumoi"),
    ("무라사 미나미츠", "村紗水蜜", "Minamitsu Murasa"), ("토라마루 쇼", "寅丸星", "Shou Toramaru"),
    ("히지리 뱌쿠렌", "聖白蓮", "Byakuren Hijiri"), ("호쥬 누에", "封獣ぬえ", "Nue Houjuu"),
    ("토요사토미미노 미코", "豊聡耳神子", "Toyosatomimi no Miko"), ("모노노베노 후토", "物部布都", "Mononobe no Futo"),
    ("후타츠이와 마미조", "二ッ岩マミゾウ", "Mamizou Futatsuiwa"), ("하타노 코코로", "秦こころ", "Hata no Kokoro"),
    ("스쿠나 신묘마루", "少名針妙丸", "Shinmyoumaru Sukuna"), ("키진 세이자", "鬼人正邪", "Seija Kijin"),
    ("헤카티아 라피스라줄리", "ヘカーティア・ラピスラズリ", "Hecatia Lapislazuli"), ("클라운피스", "クラウンピース", "Clownpiece"),
    ("순호", "純狐", "Junko"),
]
TOUHOU_GAMES = [
    ("동방홍마향", "東方紅魔郷", "The Embodiment of Scarlet Devil"), ("동방요요몽", "東方妖々夢", "Perfect Cherry Blossom"),
    ("동방영야초", "東方永夜抄", "Imperishable Night"), ("동방화영총", "東方花映塚", "Phantasmagoria of Flower View"),
    ("동방풍신록", "東方風神録", "Mountain of Faith"), ("동방지령전", "東方地霊殿", "Subterranean Animism"),
    ("동방성련선", "東方星蓮船", "Undefined Fantastic Object"), ("동방신령묘", "東方神霊廟", "Ten Desires"),
    ("동방휘침성", "東方輝針城", "Double Dealing Character"), ("동방감주전", "東方紺珠伝", "Legacy of Lunatic Kingdom"),
    ("동방천공장", "東方天空璋", "Hidden Star in Four Seasons"), ("동방귀형수", "東方鬼形獣", "Wily Beast and Weakest Creature"),
    ("동방홍룡동", "東方虹龍洞", "Unconnected Marketeers"), ("동방수왕원", "東方獣王園", "Unfinished Dream of All Living Ghost"),
    ("동방금상경", "東方錦上京", "Fossilized Wonders"),
]
LUNCH = {
    "ko": "김치찌개\n된장찌개\n돈가스\n짜장면\n짬뽕\n제육볶음\n비빔밥\n라멘\n초밥\n햄버거\n쌀국수\n떡볶이",
    "ja": "ラーメン\nカレーライス\n牛丼\nうどん\nそば\n寿司\nとんかつ\n親子丼\nオムライス\nハンバーグ\n焼き魚定食\nパスタ",
    "en": "Pizza\nBurger\nSushi\nRamen\nTacos\nPasta\nSalad\nFried chicken\nCurry\nSandwich\nPho\nDumplings",
}
PENALTY = {
    "ko": "노래 한 소절\n성대모사 하나\n커피 쏘기\n칭찬 세 마디\n스쿼트 10회\n오늘의 TMI 하나\n애교 한 번\n무사통과!",
    "ja": "歌を一節\nものまね一つ\nコーヒーをおごる\n褒め言葉を三つ\nスクワット10回\n今日のTMIを一つ\n一発ギャグ\nセーフ！",
    "en": "Sing a line\nDo an impression\nBuy coffee\nGive three compliments\n10 squats\nShare a fun fact\nTell a joke\nSafe!",
}
GACHA = {
    "ko": "# [등급 확률] 줄 아래에 그 등급의 항목을 적어요 (위 등급일수록 귀해요)\n"
          "[SSR 3]\n하쿠레이 레이무\n키리사메 마리사\n코치야 사나에\n"
          "[SR 12]\n이자요이 사쿠야\n콘파쿠 요우무\n샤메이마루 아야\n레이센\n"
          "[R 85]\n치르노\n루미아\n대요정\n요정 메이드\n케세란파사란",
    "ja": "# [レア度 確率] の行の下に、そのレア度の項目を書きます (上ほどレア)\n"
          "[SSR 3]\n博麗霊夢\n霧雨魔理沙\n東風谷早苗\n"
          "[SR 12]\n十六夜咲夜\n魂魄妖夢\n射命丸文\n鈴仙\n"
          "[R 85]\nチルノ\nルーミア\n大妖精\n妖精メイド\nケセランパサラン",
    "en": "# Write items under each [rarity rate] line (upper rarities are rarer)\n"
          "[SSR 3]\nReimu Hakurei\nMarisa Kirisame\nSanae Kochiya\n"
          "[SR 12]\nSakuya Izayoi\nYoumu Konpaku\nAya Shameimaru\nReisen\n"
          "[R 85]\nCirno\nRumia\nDaiyousei\nFairy Maid\nKedama",
}
NAMES = {  # 기본 목록 이름
    "ko": ("동방 캐릭터 ({n}명)", "동방 정규작", "점심 메뉴", "벌칙", "가챠 예시 (동방)"),
    "ja": ("東方キャラクター ({n}人)", "東方 整数作品", "ランチメニュー", "罰ゲーム", "ガチャの例 (東方)"),
    "en": ("Touhou characters ({n})", "Touhou main games", "Lunch menu", "Penalties", "Gacha example (Touhou)"),
}


def presets(lang: str) -> dict[str, str]:
    """{표시 이름: 목록 글} — 이름 앞에 📦."""
    col = {"ko": 0, "ja": 1, "en": 2}.get(lang, 0)
    names = NAMES.get(lang, NAMES["ko"])
    chars = "\n".join(c[col] for c in TOUHOU_CHARACTERS)
    games = "\n".join(g[col] if lang != "en" else f"Touhou: {g[2]}" for g in TOUHOU_GAMES)
    texts = (chars, games, LUNCH.get(lang, LUNCH["ko"]), PENALTY.get(lang, PENALTY["ko"]), GACHA.get(lang, GACHA["ko"]))
    labels = (names[0].format(n=len(TOUHOU_CHARACTERS)), *names[1:])
    return {MARK + label: text for label, text in zip(labels, texts)}
