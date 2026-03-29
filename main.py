import requests
import json
import os
import re
import feedparser

# ===== 設定 =====
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

ACCOUNTS = [
    "travismillerx13",
    "FloTrack",
    "TrackGazette",
    "Getsuriku"
]

MODEL = "gemini-3.1-flash-lite-preview"
RESULT_FILE = "results.json"

# ===== 投稿取得（syndication）=====
def get_posts_syndication(username):
    posts = []

    try:
        url = f"https://cdn.syndication.twimg.com/widgets/timelines/profile?screen_name={username}"

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json"
        }

        res = requests.get(url, headers=headers, timeout=10)

        if res.status_code != 200:
            return []

        try:
            data = res.json()
        except:
            return []

        html = data.get("body", "")

        items = re.findall(r'<div class="timeline-Tweet.*?</div>\s*</div>', html, re.DOTALL)

        for item in items:
            text = re.sub('<.*?>', '', item).strip()
            if text:
                posts.append(text)

    except:
        pass

    return posts


# ===== 保険（Google News RSS）=====
def get_posts_google(username):
    posts = []

    try:
        url = f"https://news.google.com/rss/search?q=site:twitter.com/{username}"
        feed = feedparser.parse(url)

        for e in feed.entries:
            posts.append(e.title)

    except:
        pass

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

        if "candidates" not in data:
            return None

        raw = data["candidates"][0]["content"]["parts"][0]["text"]

        start = raw.find("{")
        end = raw.rfind("}") + 1
        json_text = raw[start:end]

        return json.loads(json_text)

    except:
        return None


# ===== 保存 =====
def save(data_list):
    try:
        with open(RESULT_FILE, "w", encoding="utf-8") as f:
            json.dump(data_list, f, ensure_ascii=False, indent=2)
    except:
        pass


# ===== メイン =====
def main():
    print("start")

    all_posts = []

    for acc in ACCOUNTS:
        posts = get_posts_syndication(acc)

        if not posts:
            posts = get_posts_google(acc)

        print(acc, len(posts))

        all_posts.extend(posts)

    results = []

    for p in all_posts[:10]:  # ←API節約
        result = evaluate(p)

        if result and result.get("display"):
            results.append({
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

    save(results)

    print("done", len(results))


if __name__ == "__main__":
    main()
