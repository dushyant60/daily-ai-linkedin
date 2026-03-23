"""
Daily AI LinkedIn Post — Make.com Edition (100% Free)
"""

import os, json, re, base64
from datetime import datetime
from io import BytesIO
import textwrap

import requests
import feedparser
from openai import OpenAI
from PIL import Image, ImageDraw

OPENROUTER_KEY = os.environ["OPENROUTER_API_KEY"]
MAKE_WEBHOOK   = os.environ["MAKE_WEBHOOK_URL"]
UNSPLASH_KEY   = os.environ["UNSPLASH_ACCESS_KEY"]
IMGBB_KEY      = os.environ["IMGBB_API_KEY"]

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_KEY,
)

RSS_FEEDS = [
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://feeds.feedburner.com/venturebeat/SZYF",
    "https://www.artificialintelligence-news.com/feed/",
    "https://www.marktechpost.com/feed/",
    "https://www.theregister.com/software/ai_ml/headlines.atom",
]

# ── Safety: block these topics from ever being posted ────────────────────────
BLOCKED_KEYWORDS = [
    "adult", "nsfw", "porn", "nude", "sex", "violence", "hack", "malware", "terror", "suicide", "self-harm",
    "racist", "discrimination", "hate speech",
]

def is_safe(text: str) -> bool:
    text_lower = text.lower()
    for word in BLOCKED_KEYWORDS:
        if word in text_lower:
            print(f"🚫 SAFETY BLOCK: post contains '{word}' — aborting!")
            return False
    return True


def fetch_news() -> str:
    items = []
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:4]:
                title   = entry.get("title", "").strip()
                summary = re.sub(r"<[^>]+>", "", entry.get("summary", ""))[:300].strip()
                if title:
                    items.append(f"- {title}: {summary}")
        except Exception:
            continue
    return "\n".join(items[:20])


def generate_post(news: str) -> dict:
    today = datetime.now().strftime("%A, %B %d, %Y")
    prompt = f"""You are a professional LinkedIn thought leader in AI.
Today is {today}.

Here are today's AI news headlines:
{news}

STRICT CONTENT RULES:
- Only use facts from the headlines — never invent details
- Keep content 100% professional — no sensitive, political, adult, or controversial content
- Only post about AI technology, research, products, and business

Write a LinkedIn post with PROPER LINE BREAKS using actual newlines.

FORMAT (use real blank lines between each section):

[Hook sentence — surprising fact or question. NOT starting with 🤖]

🤖 Today in AI — {today}

🔬 or 🚀 or 💰 or 💡 *STORY HEADLINE IN CAPS*
One sentence what happened. One sentence why it matters.

🔬 or 🚀 or 💰 or 💡 *STORY HEADLINE IN CAPS*
One sentence what happened. One sentence why it matters.

🔬 or 🚀 or 💰 or 💡 *STORY HEADLINE IN CAPS*
One sentence what happened. One sentence why it matters.

[Closing question to engage readers]

#AI #ArtificialIntelligence #MachineLearning #TechNews [2-3 specific hashtags]

IMPORTANT: Each section MUST be separated by a blank line. This is critical for LinkedIn formatting.
TONE: Professional, engaging, informative. 150-250 words total.

Also pick ONE visual keyword for photo search (e.g. "robot", "microchip", "data center").

Return ONLY valid JSON, no markdown fences:
{{
  "post_text": "full post with \\n\\n between each section",
  "image_search_term": "one keyword",
  "image_headline": "5-6 word overlay text"
}}"""

    response = client.chat.completions.create(
        model="openrouter/auto",
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    data = json.loads(raw.strip())

    # Ensure proper newlines (fix escaped \\n to real \n)
    data["post_text"] = data["post_text"].replace("\\n", "\n")

    return data


def build_image(search_term: str, headline: str) -> bytes:
    img = None
    try:
        resp = requests.get(
            "https://api.unsplash.com/search/photos",
            params={"query": f"{search_term} technology", "orientation": "landscape", "per_page": 3},
            headers={"Authorization": f"Client-ID {UNSPLASH_KEY}"},
            timeout=15,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        if results:
            img_resp = requests.get(results[0]["urls"]["regular"], timeout=20)
            img_resp.raise_for_status()
            img = Image.open(BytesIO(img_resp.content)).convert("RGB")
            img = img.resize((1200, 628), Image.LANCZOS)
            print("   Unsplash photo fetched ✅")
    except Exception as e:
        print(f"   Unsplash failed ({e}), using fallback")

    if img is None:
        img = _fallback(headline)

    overlay = Image.new("RGBA", (1200, 628), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    for y in range(448, 628):
        d.rectangle([0, y, 1200, y], fill=(0, 0, 0, int(220*(y-448)/180)))
    for y in range(0, 90):
        d.rectangle([0, y, 1200, y], fill=(0, 0, 0, int(160*(1-y/90))))

    img  = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    draw.rectangle([30, 22, 238, 62], fill=(99, 102, 241))
    draw.text((44, 32), "TODAY IN AI", fill=(255, 255, 255))
    draw.text((1010, 32), datetime.now().strftime("%b %d, %Y"), fill=(210, 210, 210))

    y_pos = 628 - 120
    for line in textwrap.wrap(headline.upper(), width=38)[:2]:
        draw.text((36, y_pos), line, fill=(255, 255, 255))
        y_pos += 50

    draw.text((36, 628-26), "#AI  •  Daily Digest by Dushyant Singh", fill=(160, 160, 160))

    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _fallback(headline: str) -> Image.Image:
    themes = [
        ((15,23,42),  (99,102,241),  (248,250,252)),
        ((5,46,22),   (34,197,94),   (240,253,244)),
        ((30,27,75),  (167,139,250), (245,243,255)),
        ((12,10,9),   (251,146,60),  (255,247,237)),
        ((8,47,73),   (56,189,248),  (240,249,255)),
        ((49,10,10),  (248,113,113), (255,241,242)),
        ((31,41,55),  (251,191,36),  (255,251,235)),
    ]
    bg, ac, tx = themes[datetime.now().weekday()]
    img  = Image.new("RGB", (1200, 628), bg)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, 10, 628], fill=ac)
    draw.rectangle([60, 48, 310, 88], fill=ac)
    draw.text((72, 56), "TODAY IN AI", fill=bg)
    draw.text((60, 108), datetime.now().strftime("%B %d, %Y  •  Daily Digest"), fill=(*ac, 200))
    for i, line in enumerate(textwrap.wrap(headline.upper(), width=24)[:3]):
        draw.text((60, 175 + i*95), line, fill=tx)
    draw.text((62, 628-52), "#AI  •  #ArtificialIntelligence  •  #MachineLearning", fill=(*tx, 120))
    return img


def upload_to_imgbb(image_bytes: bytes) -> str:
    resp = requests.post(
        "https://api.imgbb.com/1/upload",
        data={
            "key": IMGBB_KEY,
            "image": base64.b64encode(image_bytes).decode("utf-8"),
            "name": f"ai-digest-{datetime.now().strftime('%Y-%m-%d')}",
        },
        timeout=30,
    )
    resp.raise_for_status()
    url = resp.json()["data"]["url"]
    print(f"   Uploaded ✅ {url}")
    return url


def send_to_make(post_text: str, image_url: str):
    resp = requests.post(
        MAKE_WEBHOOK,
        json={"post_text": post_text, "image_url": image_url},
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.status_code


def main():
    print("📰 Fetching AI news...")
    news = fetch_news()
    print(f"   Got {len(news.splitlines())} headlines\n")

    print("✍️  Generating post...")
    result = generate_post(news)

    # ── Safety check before posting anything ─────────────────────────────────
    print("🛡️  Running safety check...")
    if not is_safe(result["post_text"]):
        print("❌ Post failed safety check. Nothing posted. Check logs.")
        return
    print("   Content is safe ✅\n")

    print("\n── POST PREVIEW ──────────────────────────")
    print(result["post_text"])
    print(f"\n── IMAGE: {result['image_search_term']} → {result['image_headline']}")
    print("──────────────────────────────────────────\n")

    print("🖼️  Building image...")
    image_bytes = build_image(result["image_search_term"], result["image_headline"])
    print(f"   {len(image_bytes)//1024} KB\n")

    print("☁️  Uploading to imgbb...")
    image_url = upload_to_imgbb(image_bytes)

    print("🚀 Sending to Make.com...")
    status = send_to_make(result["post_text"], image_url)
    print(f"   ✅ Done! Status: {status}")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")


if __name__ == "__main__":
    main()