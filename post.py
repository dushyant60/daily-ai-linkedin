"""
Daily AI LinkedIn Post — Make.com Edition (100% Free)
=====================================================
Flow:
  1. Parse RSS feeds for today's AI news  (free, no key)
  2. Generate post with Google Gemini     (free tier)
  3. Generate image with Python/Pillow    (free, no API)
  4. POST everything to Make.com webhook  (free tier)
  5. Make.com posts to your LinkedIn      (personal profile, no company page)
"""

import os, json, re, base64
from datetime import datetime
from io import BytesIO
import textwrap

import requests
import feedparser
from google import genai
from PIL import Image, ImageDraw, ImageFont

# ── Config ────────────────────────────────────────────────────────────────────
GEMINI_KEY   = os.environ["GEMINI_API_KEY"]
MAKE_WEBHOOK = os.environ["MAKE_WEBHOOK_URL"]   # from Make.com scenario

client = genai.Client(api_key=GEMINI_KEY)

RSS_FEEDS = [
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://feeds.feedburner.com/venturebeat/SZYF",
    "https://www.artificialintelligence-news.com/feed/",
    "https://www.marktechpost.com/feed/",
    "https://www.theregister.com/software/ai_ml/headlines.atom",
]


# ── Step 1: Fetch AI news from RSS ───────────────────────────────────────────
def fetch_news() -> str:
    items = []
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:4]:
                title   = entry.get("title", "").strip()
                summary = re.sub(r"<[^>]+>", "", entry.get("summary", ""))[:200].strip()
                if title:
                    items.append(f"- {title}: {summary}")
        except Exception:
            continue
    return "\n".join(items[:20])


# ── Step 2: Generate post text with Gemini ───────────────────────────────────
def generate_post(news: str) -> dict:
    today = datetime.now().strftime("%A, %B %d, %Y")
    prompt = f"""You are an expert LinkedIn content creator focused on AI.
Today is {today}.

Here are today's AI news headlines:
{news}

Write a LinkedIn post in this format:
- Header: "🤖 Today in AI — {today}"
- One punchy hook sentence
- 3-4 news items using: 🔬 research, 🚀 product/tool, 💰 funding, 💡 insight
- Each item: bold headline (using *asterisks*) + 1-2 sentence plain-English summary
- One engaging closing question
- 6-8 hashtags at the end (#AI #ArtificialIntelligence #MachineLearning etc.)

Tone: Conversational and engaging, like a knowledgeable friend.
Length: 150-250 words.

Also pick ONE short headline (max 8 words) from the biggest story for the image.

Return ONLY valid JSON, no markdown:
{{
  "post_text": "full LinkedIn post here",
  "image_headline": "short headline for image"
}}"""

    response = client.models.generate_content(model='gemini-2.0-flash', contents=prompt)
    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


# ── Step 3: Generate image with Python ───────────────────────────────────────
def generate_image(headline: str) -> str:
    """Returns base64-encoded PNG string."""
    W, H = 1200, 628

    # Rotate color theme by day of week
    themes = [
        {"bg": (15, 23, 42),   "accent": (99, 102, 241),  "txt": (248, 250, 252)},  # Mon indigo
        {"bg": (5, 46, 22),    "accent": (34, 197, 94),   "txt": (240, 253, 244)},  # Tue green
        {"bg": (30, 27, 75),   "accent": (167, 139, 250), "txt": (245, 243, 255)},  # Wed purple
        {"bg": (12, 10, 9),    "accent": (251, 146, 60),  "txt": (255, 247, 237)},  # Thu orange
        {"bg": (8, 47, 73),    "accent": (56, 189, 248),  "txt": (240, 249, 255)},  # Fri blue
        {"bg": (49, 10, 10),   "accent": (248, 113, 113), "txt": (255, 241, 242)},  # Sat red
        {"bg": (31, 41, 55),   "accent": (251, 191, 36),  "txt": (255, 251, 235)},  # Sun amber
    ]
    t = themes[datetime.now().weekday()]
    bg, ac, tx = t["bg"], t["accent"], t["txt"]

    img  = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)

    # Left accent bar
    draw.rectangle([0, 0, 10, H], fill=ac)

    # "TODAY IN AI" badge
    draw.rectangle([60, 48, 310, 88], fill=ac)
    draw.text((72, 56), "TODAY IN AI", fill=bg)

    # Date
    draw.text((60, 108), datetime.now().strftime("%B %d, %Y  •  Daily Digest"), fill=(*ac, 200))

    # Main headline — large, wrapped
    lines = textwrap.wrap(headline.upper(), width=24)
    for i, line in enumerate(lines[:3]):
        y = 175 + i * 95
        # Shadow
        draw.text((63, y+3), line, fill=(*bg, 180))
        draw.text((60, y),   line, fill=tx)

    # Decorative grid dots bottom-right
    for i in range(6):
        for j in range(4):
            x = W - 100 - i * 28
            y = H - 90  - j * 28
            r = 3 if (i+j) % 2 == 0 else 1
            draw.ellipse([x-r, y-r, x+r, y+r], fill=(*ac, 100))

    # Horizontal rule
    draw.rectangle([60, H-70, W-60, H-68], fill=(*ac, 80))

    # Footer
    draw.text((62, H-52), "#AI  •  #ArtificialIntelligence  •  #MachineLearning", fill=(*tx, 120))
    draw.text((W-200, H-52), "Daily AI Digest", fill=(*ac, 160))

    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


# ── Step 4: Send to Make.com webhook ─────────────────────────────────────────
def send_to_make(post_text: str, image_b64: str, headline: str):
    payload = {
        "post_text":      post_text,
        "image_base64":   image_b64,
        "image_filename": f"ai-digest-{datetime.now().strftime('%Y-%m-%d')}.png",
        "headline":       headline,
        "posted_at":      datetime.now().isoformat(),
    }
    resp = requests.post(
        MAKE_WEBHOOK,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.status_code


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("📰 Fetching AI news from RSS feeds...")
    news = fetch_news()
    print(f"   Got {len(news.splitlines())} headlines\n")

    print("✍️  Generating post with Gemini...")
    result = generate_post(news)
    print("\n── POST PREVIEW ──────────────────────────")
    print(result["post_text"])
    print(f"\n── IMAGE HEADLINE: {result['image_headline']}")
    print("──────────────────────────────────────────\n")

    print("🎨 Generating image...")
    image_b64 = generate_image(result["image_headline"])
    print(f"   Image ready ({len(image_b64)//1024} KB base64)\n")

    print("🚀 Sending to Make.com webhook...")
    status = send_to_make(result["post_text"], image_b64, result["image_headline"])
    print(f"   ✅ Webhook received! Status: {status}")
    print(f"   Make.com will post to LinkedIn now.")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")


if __name__ == "__main__":
    main()
