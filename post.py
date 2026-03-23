"""
Daily AI LinkedIn Post — Make.com Edition (100% Free)
=====================================================
Flow:
  1. Parse RSS feeds for today's AI news  (free, no key)
  2. Generate post with OpenRouter        (free tier)
  3. Fetch relevant image from Unsplash   (free API)
  4. Upload image to imgbb                (free, returns public URL)
  5. Send post_text + image_url to Make.com webhook
  6. Make.com posts image + text to LinkedIn
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

# ── Safety guardrails ─────────────────────────────────────────────────────────
BLOCKED_KEYWORDS = [
    "adult", "explicit", "nsfw", "porn", "nude", "sex", "violence",
    "weapon", "drug", "hack", "malware", "terror", "suicide", "self-harm",
    "racist", "discrimination", "hate speech",
]

def is_safe(text: str) -> bool:
    text_lower = text.lower()
    for word in BLOCKED_KEYWORDS:
        if word in text_lower:
            print(f"🚫 SAFETY BLOCK: post contains '{word}' — aborting!")
            return False
    return True


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


# ── Step 2: Generate post text with OpenRouter ───────────────────────────────
def generate_post(news: str) -> dict:
    today = datetime.now().strftime("%A, %B %d, %Y")
    prompt = f"""You are an expert LinkedIn content creator focused on AI.
Today is {today}.

Here are today's AI news headlines:
{news}

Write a LinkedIn post with PROPER LINE BREAKS. Each section must be separated by a blank line.

FORMAT:
[Hook sentence — one surprising fact or question. Do NOT start with 🤖]

🤖 Today in AI — {today}

🔬 or 🚀 or 💰 or 💡 *STORY HEADLINE IN CAPS*
One sentence what happened. One sentence why it matters.

🔬 or 🚀 or 💰 or 💡 *STORY HEADLINE IN CAPS*
One sentence what happened. One sentence why it matters.

🔬 or 🚀 or 💰 or 💡 *STORY HEADLINE IN CAPS*
One sentence what happened. One sentence why it matters.

[One closing question to engage readers]

#AI #ArtificialIntelligence #MachineLearning #TechNews [2-3 specific hashtags]

RULES:
- Only use facts from the headlines — never invent details
- Keep content 100% professional — AI technology only
- IMPORTANT: use \\n\\n between every section for proper LinkedIn formatting
- Tone: conversational, engaging, like a knowledgeable friend
- Length: 150-250 words

Also pick ONE visual keyword from the biggest story for Unsplash photo search
(e.g. "robot", "microchip", "data center", "neural network").

Return ONLY valid JSON, no markdown fences:
{{
  "post_text": "full post with \\n\\n between each section",
  "image_headline": "short 5-6 word headline for image overlay",
  "image_search_term": "one visual keyword"
}}"""

    response = client.chat.completions.create(
        model="openrouter/free",
        messages=[{"role": "user", "content": prompt}],
        extra_body={"reasoning": {"enabled": True}}
    )
    raw = response.choices[0].message.content.strip()
    if not raw:
        raise ValueError("AI returned empty response — re-run the workflow to retry")
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    data = json.loads(raw.strip())

    # Ensure real newlines (fix escaped \\n to actual \n)
    data["post_text"] = data["post_text"].replace("\\n", "\n")

    return data


# ── Step 3: Fetch Unsplash photo + overlay branding ──────────────────────────
def build_image(search_term: str, headline: str) -> bytes:
    """Fetch Unsplash photo, add overlay, return PNG bytes."""
    img = None

    try:
        resp = requests.get(
            "https://api.unsplash.com/search/photos",
            params={
                "query": f"{search_term} technology",
                "orientation": "landscape",
                "per_page": 3,
            },
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
        print(f"   Unsplash failed ({e}), using fallback graphic")

    # Fallback: clean dark branded graphic
    if img is None:
        img = _fallback_graphic(headline)
        buf = BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue()

    # ── Dark overlay for readability ──────────────────────────────────────────
    overlay = Image.new("RGBA", (1200, 628), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    for y in range(448, 628):
        ov_draw.rectangle([0, y, 1200, y], fill=(0, 0, 0, int(220*(y-448)/180)))
    for y in range(0, 90):
        ov_draw.rectangle([0, y, 1200, y], fill=(0, 0, 0, int(160*(1-y/90))))

    img  = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Badge top-left
    draw.rectangle([30, 22, 238, 62], fill=(99, 102, 241))
    draw.text((44, 32), "TODAY IN AI", fill=(255, 255, 255))

    # Date top-right
    draw.text((1010, 32), datetime.now().strftime("%b %d, %Y"), fill=(210, 210, 210))

    # Headline bottom
    y_pos = 628 - 120
    for line in textwrap.wrap(headline.upper(), width=38)[:2]:
        draw.text((36, y_pos), line, fill=(255, 255, 255))
        y_pos += 50

    # Branding footer
    draw.text((36, 628-26), "#AI  •  Daily Digest by Dushyant Singh", fill=(160, 160, 160))

    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


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
        draw.text((60, 175 + i*95), line, fill=tx)
    for i in range(6):
        for j in range(4):
            x, y = 1200 - 100 - i*28, 628 - 90 - j*28
            r = 3 if (i+j) % 2 == 0 else 1
            draw.ellipse([x-r, y-r, x+r, y+r], fill=(*ac, 100))
    draw.rectangle([60, 628-70, 1200-60, 628-68], fill=(*ac, 80))
    draw.text((62, 628-52), "#AI  •  #ArtificialIntelligence  •  #MachineLearning", fill=(*tx, 120))
    draw.text((1200-200, 628-52), "Daily AI Digest", fill=(*ac, 160))
    return img


# ── Step 4: Upload image to imgbb → get public URL ───────────────────────────
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


# ── Step 5: Send to Make.com webhook ─────────────────────────────────────────
def send_to_make(post_text: str, image_url: str):
    payload = {
        "post_text": post_text,
        "image_url": image_url,
        "posted_at": datetime.now().isoformat(),
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

    print("✍️  Generating post with OpenRouter (free)...")
    result = generate_post(news)

    # Safety check before posting anything
    print("🛡️  Running safety check...")
    if not is_safe(result["post_text"]):
        print("❌ Post blocked by safety filter. Nothing posted.")
        return
    print("   Safe ✅\n")

    print("\n── POST PREVIEW ──────────────────────────")
    print(result["post_text"])
    print(f"\n── IMAGE: {result['image_search_term']} → {result['image_headline']}")
    print("──────────────────────────────────────────\n")

    print(f"🖼️  Fetching image: '{result['image_search_term']}'...")
    image_bytes = build_image(result["image_search_term"], result["image_headline"])
    print(f"   {len(image_bytes)//1024} KB\n")

    print("☁️  Uploading to imgbb...")
    image_url = upload_to_imgbb(image_bytes)

    print("🚀 Sending to Make.com webhook...")
    status = send_to_make(result["post_text"], image_url)
    print(f"   ✅ Webhook received! Status: {status}")
    print(f"   Make.com will post to LinkedIn now.")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")


if __name__ == "__main__":
    main()