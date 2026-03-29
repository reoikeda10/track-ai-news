import time
import requests
import json
import os
import re

# ===== 設定 =====
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

ACCOUNTS = [
    "travismillerx13",
    "FloTrack",
    "TrackGazette",
    "Getsuriku"
]

CHECK_INTERVAL = 120
MODEL = "gemini-3.1-flash-lite-preview"
RESULT_FILE = "results.json"

seen_ids = set()

# ===== 投稿取得（syndication API）=====
def get_posts(username):
    posts = []

    try:
        url = f"https://cdn.syndication.twimg.com/widgets/timelines/profile?screen_name={username}"

        res = requests.get(url, timeout=10)
        data = res.json()

        html = data.get("body", "")

        # 投稿ブロックごと抽出
        items = re.findall(r'<div class="timeline-Tweet.*?</div>\s*</div>', html, re.DOTALL)

        for item in items:
            try:
                # テキスト抽出
                text = re.sub('<.*?>', '', item)
                text = text.strip()

                # tweet id抽出
                match = re.search(r'data-tweet-id="(\d+)"', item)
                tweet_id = match.group(1) if match else text[:50]

                if tweet_id not in seen_ids:
                    seen_ids.add(tweet_id)
                    posts.append(text)

            except:
                continue

    except Exception as e:
        print("syndication error:", username, e)

    return posts


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
- その他重要情報（noteに含めてもOK）

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

        # エラーチェック
        if "candidates" not in data:
            print("Gemini API error:", data)
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


# ===== メイン =====
while True:
    try:
        print("checking...")

        all_posts = []

        for acc in ACCOUNTS:
            posts = get_posts(acc)

            if posts:
                print(f"{acc}: {len(posts)}件取得")

            all_posts.extend(posts)

        if all_posts:
            for p in all_posts:
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
