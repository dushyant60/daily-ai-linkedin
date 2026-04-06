"""
Daily AI LinkedIn Post — Make.com Edition (100% Free)
=====================================================
Flow:
  1. Parse RSS feeds for today's AI news  (free, no key)
  2. Generate post with OpenRouter        (free tier)
  3. Fetch relevant image from Unsplash   (free API, smarter search)
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
    prompt = (
        f"You are a sharp, opinionated LinkedIn creator who covers AI daily.\n"
        f"You write like a knowledgeable friend — clear, punchy, with a real point of view.\n"
        f"Today is {today}.\n\n"
        f"Here are today's AI headlines:\n{news}\n\n"
        "Return ONLY a valid JSON object — no markdown, no explanation, just JSON.\n\n"
        "Rules:\n"
        "- NEVER invent model names, version numbers, company names, or statistics not in the headlines\n"
        "- Do NOT use \"It matters because\" or \"Why it matters:\" — weave significance naturally\n"
        "- Each story body = exactly 2 sentences\n"
        "- Pick the 3 most interesting stories, not just the first 3\n"
        "- hook: one punchy sentence — bold claim, surprising stat, or provocative question. Do NOT start with \"I\" or emoji\n"
        "- closing: one opinionated question or hot take. NOT \"share your thoughts\"\n"
        "- Emoji per story — pick best fit: research/models=, launches/features=, funding/business=, policy/legal=, partnerships=, trends=\n"
        "- image_search_terms: three specific Unsplash phrases from the biggest story, ordered most-to-least specific\n\n"
        "JSON schema (return exactly this structure):\n"
        "{\n"
        "  \"hook\": \"one punchy hook sentence\",\n"
        "  \"stories\": [\n"
        "    {\"emoji\": \"X\", \"headline\": \"HEADLINE IN CAPS MAX 8 WORDS\", \"body\": \"Sentence 1. Sentence 2.\"},\n"
        "    {\"emoji\": \"X\", \"headline\": \"HEADLINE IN CAPS MAX 8 WORDS\", \"body\": \"Sentence 1. Sentence 2.\"},\n"
        "    {\"emoji\": \"X\", \"headline\": \"HEADLINE IN CAPS MAX 8 WORDS\", \"body\": \"Sentence 1. Sentence 2.\"}\"\n"
        "  ],\n"
        "  \"closing\": \"opinionated closing question or hot take\",\n"
        "  \"hashtags\": \"#AI #ArtificialIntelligence #MachineLearning #TechNews #Specific1 #Specific2\",\n"
        "  \"image_headline\": \"5-6 word image overlay headline\",\n"
        "  \"image_search_terms\": [\"specific phrase\", \"medium phrase\", \"broad fallback\"]\n"
        "}"
    )

    for attempt in range(1, 4):
        try:
            print(f"   Attempt {attempt}/3...")
            response = client.chat.completions.create(
                model="openrouter/free",
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.choices[0].message.content.strip()
            if not raw:
                raise ValueError("Empty response from model")

            # Strip markdown fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()

            data = json.loads(raw)

            # Validate all required keys are present and non-empty
            for key in ["hook", "stories", "closing", "hashtags", "image_headline", "image_search_terms"]:
                if not data.get(key):
                    raise ValueError(f"Missing or empty field: '{key}'")
            if len(data["stories"]) < 3:
                raise ValueError(f"Only {len(data['stories'])} stories returned, need 3")
            for i, s in enumerate(data["stories"]):
                if not s.get("headline") or not s.get("body"):
                    raise ValueError(f"Story {i+1} is incomplete")

            # Assemble post_text from structured fields
            lines = [
                data["hook"],
                "",
                f"\U0001f916 Today in AI \u2014 {today}",
            ]
            for story in data["stories"]:
                lines.append("")
                lines.append(f"{story['emoji']} {story['headline']}")
                lines.append(story["body"])
            lines.append("")
            lines.append(data["closing"])
            lines.append("")
            lines.append(data["hashtags"])
            data["post_text"] = "\n".join(lines)

            print(f"   Post generated successfully")
            return data

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            print(f"   Attempt {attempt} failed: {e}")
            if attempt == 3:
                raise RuntimeError("All 3 attempts failed — check your OpenRouter quota or try again later")
            continue

# ── Step 3: Fetch Unsplash photo + overlay branding ──────────────────────────
def build_image(search_terms: list[str], headline: str) -> bytes:
    """Try each search term in order until Unsplash returns a good result."""
    img = None

    for term in search_terms:
        try:
            print(f"   Trying Unsplash: '{term}'...")
            resp = requests.get(
                "https://api.unsplash.com/search/photos",
                params={
                    "query": term,
                    "orientation": "landscape",
                    "per_page": 3,
                    "content_filter": "high",
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
                print(f"   ✅ Got image for: '{term}'")
                break  # stop as soon as we get a hit
        except Exception as e:
            print(f"   ❌ Failed for '{term}': {e}")
            continue

    # Fallback: clean dark branded graphic
    if img is None:
        print("   All terms failed, using fallback graphic")
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

    print("\n── POST PREVIEW ──────────────────────────")
    print(result["post_text"])
    print(f"\n── IMAGE TERMS: {result['image_search_terms']} → {result['image_headline']}")
    print("──────────────────────────────────────────\n")

    print(f"🖼️  Fetching image (trying {len(result['image_search_terms'])} terms)...")
    image_bytes = build_image(result["image_search_terms"], result["image_headline"])
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