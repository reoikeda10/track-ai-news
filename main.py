import time
import feedparser
import requests
import json
import os

# ===== 設定 =====
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

ACCOUNTS = [
    "travismillerx13",
    "FloTrack",
    "TrackGazette",
    "Getsuriku"
]

CHECK_INTERVAL = 120  # ←少し長め（安定化）

MODEL = "gemini-3.1-flash-lite-preview"
RESULT_FILE = "results.json"

# 複数Nitter（重要）
NITTER_INSTANCES = [
    "https://nitter.net",
    "https://nitter.poast.org",
    "https://nitter.privacydev.net",
    "https://nitter.rawbit.ch"
]

seen_ids = set()

# ===== RSS取得（フォールバック付き）=====
def get_feed(username):
    for base in NITTER_INSTANCES:
        try:
            url = f"{base}/{username}/rss"

            feed = feedparser.parse(
                url,
                request_headers={"User-Agent": "Mozilla/5.0"}
            )

            if feed.entries:
                print(f"OK: {username} ({base})")
                return feed

        except Exception as e:
            print("RSS fail:", base, username, e)

    print("RSS全滅:", username)
    return None


# ===== Gemini =====
def evaluate(text):
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={GEMINI_API_KEY}"

        prompt = f"""
あなたは陸上競技の専門家です。

以下の投稿から情報を正確に抽出し、その記録の価値を評価してください。

【抽出項目】
- 日時（date）
- 選手名（athlete）
- 国籍（country）
- 種目（event）
- 記録（mark）
- 風速（wind）
- 場所（location）
- 大会名（competition）
- 備考（note）

不明な場合は null

【評価ルール】
- 向かい風は評価
- 追い風+2.1以上でも記録が突出していれば減点しない
- WR, WL, NR, PBは加点
- 若手（U20）は加点
- 大会の格も考慮

【出力形式（JSONのみ）】
{{
 "display": true/false,
 "score": 0-100,
 "event": "",
 "mark": "",
 "wind": "",
 "athlete": "",
 "country": "",
 "competition": "",
 "location": "",
 "date": "",
 "note": "",
 "reason": ""
}}

投稿：
{text}
"""

        res = requests.post(
            url,
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=15
        )

        data = res.json()

        # ===== ここが重要 =====
        if "candidates" not in data:
            print("Gemini APIエラー:", data)
            return None

        raw = data["candidates"][0]["content"]["parts"][0]["text"]

        # JSON抽出
        start = raw.find("{")
        end = raw.rfind("}") + 1
        json_text = raw[start:end]

        return json.loads(json_text)

    except Exception as e:
        print("Gemini error:", e)
        return None


# ===== 保存 =====
def save(data):
    try:
        with open(RESULT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
    except Exception as e:
        print("Save error:", e)


# ===== 投稿取得 =====
def get_posts():
    new_posts = []

    for acc in ACCOUNTS:
        feed = get_feed(acc)

        if not feed:
            continue

        for entry in feed.entries:
            try:
                post_id = entry.id

                if post_id not in seen_ids:
                    seen_ids.add(post_id)

                    text = entry.title
                    new_posts.append(text)

            except Exception as e:
                print("Entry error:", e)

    return new_posts


# ===== メインループ =====
while True:
    try:
        print("checking...")

        posts = get_posts()

        if posts:
            print(f"{len(posts)}件取得")

            for p in posts:
                result = evaluate(p)

                if result and result.get("display"):
                    save({
                        "text": p,
                        "score": result.get("score"),
                        "event": result.get("event"),
                        "mark": result.get("mark"),
                        "wind": result.get("wind"),
                        "athlete": result.get("athlete"),
                        "country": result.get("country"),
                        "competition": result.get("competition"),
                        "location": result.get("location"),
                        "date": result.get("date"),
                        "note": result.get("note"),
                        "reason": result.get("reason")
                    })

                    print("saved:", p)

        else:
            print("no new")

    except Exception as e:
        print("MAIN ERROR:", e)

    time.sleep(CHECK_INTERVAL)
