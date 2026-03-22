"""
Daily AI LinkedIn Post — Make.com Edition (100% Free)
=====================================================
Flow:
  1. Parse RSS feeds for today's AI news  (free, no key)
  2. Generate post with OpenRouter        (free tier)
  3. Fetch relevant image from Unsplash   (free API, no billing)
  4. POST everything to Make.com webhook  (free tier)
  5. Make.com posts to your LinkedIn      (personal profile)
"""

import os, json, re, base64
from datetime import datetime
from io import BytesIO
import textwrap

import requests
import feedparser
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont

# ── Config ────────────────────────────────────────────────────────────────────
OPENROUTER_KEY = os.environ["OPENROUTER_API_KEY"]
MAKE_WEBHOOK   = os.environ["MAKE_WEBHOOK_URL"]
UNSPLASH_KEY   = os.environ["UNSPLASH_ACCESS_KEY"]   # free at unsplash.com/developers

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


# ── Step 1: Fetch AI news from RSS ───────────────────────────────────────────
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


# ── Step 2: Generate post via OpenRouter ─────────────────────────────────────
def generate_post(news: str) -> dict:
    today = datetime.now().strftime("%A, %B %d, %Y")
    prompt = f"""You are a top LinkedIn thought leader in AI with 100k+ followers.
Today is {today}.

Here are today's verified AI news headlines:
{news}

Your task: Write a LinkedIn post that stops people mid-scroll.

STRICT RULES:
- Only use facts from the headlines above — never invent or assume details
- Every claim must come directly from the provided news

POST FORMAT:
Line 1: A bold surprising hook — one sentence that makes people STOP scrolling.
         Use a surprising stat, provocative question, or "nobody is talking about this" angle.
         Do NOT start with "🤖 Today in AI"

Line 2: Empty line

Line 3: "🤖 Today in AI — {today}"

Line 4: Empty line

Then 3-4 stories, each like this:
[emoji] *HEADLINE IN CAPS*
One punchy sentence: what happened. One sentence: why it matters to the reader personally.

Emojis by category:
🔬 research/papers  🚀 product launches  💰 funding/acquisitions  💡 insights/trends

Empty line after all stories.

Closing: One thought-provoking question inviting readers to share their opinion.
Make it personal — "What do YOU think..." or "Are you already using..."

Final line: 6-8 hashtags: #AI #ArtificialIntelligence #MachineLearning #TechNews + 2-3 specific ones

TONE: Write like a smart friend texting breaking news. Short sentences. High energy. No fluff.

Also pick ONE visual keyword from the biggest story for an Unsplash photo search
(e.g. "robot", "microchip", "data center", "neural network", "computer vision").

Return ONLY valid JSON, no markdown fences:
{{
  "post_text": "full LinkedIn post here",
  "image_search_term": "one visual keyword for photo search",
  "image_headline": "short 5-6 word overlay text for image"
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
    return json.loads(raw.strip())


# ── Step 3: Fetch real photo from Unsplash + overlay text ────────────────────
def fetch_image(search_term: str, headline: str) -> str:
    """Fetch Unsplash photo, overlay branding, return base64 PNG."""
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
            photo_url = results[0]["urls"]["regular"]
            img_resp  = requests.get(photo_url, timeout=20)
            img_resp.raise_for_status()
            img = Image.open(BytesIO(img_resp.content)).convert("RGB")
            img = img.resize((1200, 628), Image.LANCZOS)
            print(f"   Unsplash photo fetched ✅")
    except Exception as e:
        print(f"   Unsplash failed ({e}), using fallback graphic")

    # Fallback: generate clean dark graphic
    if img is None:
        img = _fallback_graphic(headline)

    # ── Overlay ───────────────────────────────────────────────────────────────
    overlay = Image.new("RGBA", (1200, 628), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)

    # Dark gradient at bottom for text readability
    for y in range(448, 628):
        alpha = int(220 * (y - 448) / 180)
        ov_draw.rectangle([0, y, 1200, y], fill=(0, 0, 0, alpha))

    # Dark strip at top for badge
    for y in range(0, 90):
        alpha = int(160 * (1 - y / 90))
        ov_draw.rectangle([0, y, 1200, y], fill=(0, 0, 0, alpha))

    img  = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    # "TODAY IN AI" badge — top left
    draw.rectangle([30, 22, 238, 62], fill=(99, 102, 241))
    draw.text((44, 32), "TODAY IN AI", fill=(255, 255, 255))

    # Date — top right
    draw.text((1010, 32), datetime.now().strftime("%b %d, %Y"), fill=(210, 210, 210))

    # Headline — bottom, large text
    lines = textwrap.wrap(headline.upper(), width=38)
    y_pos = 628 - 120
    for line in lines[:2]:
        draw.text((36, y_pos), line, fill=(255, 255, 255))
        y_pos += 50

    # Branding footer
    draw.text((36, 628 - 26), "#AI  •  #ArtificialIntelligence  •  Daily Digest by Dushyant", fill=(160, 160, 160))

    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _fallback_graphic(headline: str) -> Image.Image:
    themes = [
        {"bg": (15, 23, 42),  "accent": (99, 102, 241),  "txt": (248, 250, 252)},
        {"bg": (5, 46, 22),   "accent": (34, 197, 94),   "txt": (240, 253, 244)},
        {"bg": (30, 27, 75),  "accent": (167, 139, 250), "txt": (245, 243, 255)},
        {"bg": (12, 10, 9),   "accent": (251, 146, 60),  "txt": (255, 247, 237)},
        {"bg": (8, 47, 73),   "accent": (56, 189, 248),  "txt": (240, 249, 255)},
        {"bg": (49, 10, 10),  "accent": (248, 113, 113), "txt": (255, 241, 242)},
        {"bg": (31, 41, 55),  "accent": (251, 191, 36),  "txt": (255, 251, 235)},
    ]
    t  = themes[datetime.now().weekday()]
    bg, ac, tx = t["bg"], t["accent"], t["txt"]
    img  = Image.new("RGB", (1200, 628), bg)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, 10, 628], fill=ac)
    draw.rectangle([60, 48, 310, 88], fill=ac)
    draw.text((72, 56), "TODAY IN AI", fill=bg)
    draw.text((60, 108), datetime.now().strftime("%B %d, %Y  •  Daily Digest"), fill=(*ac, 200))
    for i, line in enumerate(textwrap.wrap(headline.upper(), width=24)[:3]):
        draw.text((60, 175 + i * 95), line, fill=tx)
    for i in range(6):
        for j in range(4):
            x, y = 1200 - 100 - i*28, 628 - 90 - j*28
            r = 3 if (i+j) % 2 == 0 else 1
            draw.ellipse([x-r, y-r, x+r, y+r], fill=(*ac, 100))
    draw.text((62, 628-52), "#AI  •  #ArtificialIntelligence  •  #MachineLearning", fill=(*tx, 120))
    return img


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

    print("✍️  Generating post with OpenRouter...")
    result = generate_post(news)
    print("\n── POST PREVIEW ──────────────────────────")
    print(result["post_text"])
    print(f"\n── IMAGE SEARCH: {result['image_search_term']}")
    print(f"── IMAGE HEADLINE: {result['image_headline']}")
    print("──────────────────────────────────────────\n")

    print(f"🖼️  Fetching image from Unsplash: '{result['image_search_term']}'...")
    image_b64 = fetch_image(result["image_search_term"], result["image_headline"])
    print(f"   Image ready ({len(image_b64)//1024} KB)\n")

    print("🚀 Sending to Make.com webhook...")
    status = send_to_make(result["post_text"], image_b64, result["image_headline"])
    print(f"   ✅ Webhook received! Status: {status}")
    print(f"   Make.com will post to LinkedIn now.")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")


if __name__ == "__main__":
    main()