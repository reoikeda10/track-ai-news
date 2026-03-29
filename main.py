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

CHECK_INTERVAL = 60
MODEL = "gemini-3.1-flash-lite-preview"

RESULT_FILE = "results.json"

seen_ids = set()

# ===== フィルタ =====
def is_candidate(text):
    keywords = ["m","WR","WL","NR","PB","jump","throw"]
    return any(k.lower() in text.lower() for k in keywords)

# ===== Gemini =====
def evaluate(text):
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={GEMINI_API_KEY}"

        res = requests.post(url, json={
            "contents":[{"parts":[{"text":prompt}]}]
        }, timeout=10)

        data = res.json()

        raw = data["candidates"][0]["content"]["parts"][0]["text"]

        return json.loads(raw)

    except Exception as e:
        print("Gemini error:", e)
        return None

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
- 備考（note）※PB, NR, U20など
- その他重要情報（noteに含めてもOK）

不明な場合は null

【評価ルール】
- 向かい風は評価
- 追い風+2.1以上でも記録が突出していれば減点しない
- WR, WL, NR, PBは加点
- 若手（U20）は加点
- 大会の格も考慮

【出力形式（JSONのみ）】
{
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
}

【重要】
- JSON以外は一切出力しない
- 推測しすぎない（不明はnull）
- 投稿文の情報を最大限使う


投稿:
{text}
"""

        res = requests.post(url, json={
            "contents":[{"parts":[{"text":prompt}]}]
        }, timeout=10)

        data = res.json()

        text_out = data["candidates"][0]["content"]["parts"][0]["text"]

        return json.loads(text_out)

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

# ===== RSS =====
def get_posts():
    new = []

    for acc in ACCOUNTS:
        try:
            feed = feedparser.parse(f"https://nitter.net/{acc}/rss")

            for e in feed.entries:
                if e.id not in seen_ids:
                    seen_ids.add(e.id)

                    if is_candidate(e.title):
                        new.append(e.title)

        except Exception as e:
            print("RSS error:", acc, e)

    return new

# ===== メイン =====
while True:
    try:
        print("checking...")

        posts = get_posts()

        if posts:
            print(f"{len(posts)}件処理")

            for p in posts:
                result = evaluate(p)

                if result and result.get("display")
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
