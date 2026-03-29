import time
import feedparser
import requests
import json
import os

# ===== 設定 =====
GEMINI_API_KEY = "AIzaSyBKcxpFOgVMvSN-S2xeirP3dilDSuVwoQ4"  # ←入れる

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
    keywords = [
    ]
    return any(k.lower() in text.lower() for k in keywords)

# ===== Gemini =====
def evaluate(text):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={GEMINI_API_KEY}"

    prompt = f"""
陸上の速報価値を「種目、記録、風速、国名、備考、WRやNRなど、年齢、その場のコンディション、その他文からわかること」から評価してください。

出力(JSONのみ):
{{
 "score": 0-100,
 "display": true/false,
 "event": "",
 "mark": "",
 "reason": ""
}}

投稿:
{text}
"""

    res = requests.post(url, json={
        "contents":[{"parts":[{"text":prompt}]}]
    })

    try:
        return res.json()["candidates"][0]["content"]["parts"][0]["text"]
    except:
        return None

# ===== 保存 =====
def save(data):
    if not os.path.exists(RESULT_FILE):
        with open(RESULT_FILE, "w") as f:
            pass

    with open(RESULT_FILE, "a", encoding="utf-8") as f:
        f.write(data + "\n")

# ===== RSS =====
def get_posts():
    new = []
    for acc in ACCOUNTS:
        feed = feedparser.parse(f"https://nitter.net/{acc}/rss")

        for e in feed.entries:
            if e.id not in seen_ids:
                seen_ids.add(e.id)

                if is_candidate(e.title):
                    new.append(e.title)

    return new

# ===== メイン =====
while True:
    print("checking...")

    posts = get_posts()

    if posts:
        for p in posts:
            result = evaluate(p)

            if result:
                try:
                    data = json.loads(result)

                    if data.get("display"):
                        save(json.dumps({
                            "text": p,
                            "score": data.get("score"),
                            "event": data.get("event"),
                            "mark": data.get("mark"),
                            "reason": data.get("reason")
                        }, ensure_ascii=False))

                        print("saved:", p)

                except:
                    pass

    else:
        print("no new")

    time.sleep(CHECK_INTERVAL)
