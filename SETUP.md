# Daily AI LinkedIn Post — Make.com Setup Guide

100% free. Posts to your personal LinkedIn. No company page needed.

---

## Overview

GitHub Actions (free) → generates post with Gemini (free) → sends to Make.com
webhook (free) → Make.com posts to your LinkedIn personal profile (free).

Only 2 API keys needed: Gemini + Make.com webhook URL.

---

## Part A — Get your free Gemini API key

1. Go to: https://aistudio.google.com/app/apikey
2. Sign in with any Google account
3. Click "Create API Key" → copy it (looks like `AIzaSy...`)

No credit card. Free tier = 1500 requests/day.

---

## Part B — Set up Make.com (the LinkedIn posting part)

This is where the magic happens — Make.com logs into LinkedIn AS YOU.

### B1. Create a free Make.com account
1. Go to https://make.com
2. Sign up free (no credit card needed)
3. Free tier = 1000 operations/month — you need ~60/month

### B2. Create a new Scenario
1. Click "Create a new scenario"
2. Click the "+" button to add your first module
3. Search for **"Webhooks"** → select **"Custom webhook"**
4. Click "Add" → name it "LinkedIn Post Trigger" → click Save
5. Make.com gives you a **webhook URL** — copy it now!
   It looks like: `https://hook.eu1.make.com/abc123xyz...`
   ⚠️ This is your `MAKE_WEBHOOK_URL` secret for GitHub

### B3. Add the LinkedIn module
1. Click the "+" after the webhook module
2. Search for **"LinkedIn"** → select **"Create a Post"**
3. Click "Add a connection" → "Continue with LinkedIn"
4. Sign in with YOUR LinkedIn account (personal profile)
5. Allow the permissions
6. Now configure the post fields:

   | Field          | Value to set                              |
   |----------------|-------------------------------------------|
   | Visibility     | `PUBLIC`                                  |
   | Commentary     | Click the webhook icon → select `post_text` |

### B4. Add the image (optional but recommended)
To include the generated image:

1. Click "+" between Webhook and LinkedIn modules
2. Add **"HTTP" → "Get a file"** — we'll convert base64 to file
   Actually easier: use **"Tools" → "Base64 Decode"**
   - Input: `{{1.image_base64}}` (from webhook data)
3. Then in LinkedIn module, under "Media":
   - Upload URL: connect the decoded image output

   **Simpler alternative** — text-only post first, add image later once comfortable.

### B5. Turn on the scenario
1. Click the toggle at the bottom left to turn scenario **ON**
2. Click "Save"
3. Your scenario is now live and waiting for webhooks!

### B6. Test the webhook
To verify it's working, send a test from your terminal:
```bash
curl -X POST YOUR_WEBHOOK_URL \
  -H "Content-Type: application/json" \
  -d '{"post_text": "Test post from my automation! 🤖 #AI", "image_base64": "", "headline": "Test"}'
```
Check Make.com → your scenario should show a green checkmark.
Check LinkedIn — the test post should appear on your profile!

---

## Part C — Set up GitHub repository

1. Go to https://github.com/new → create a **private** repo
2. Upload these files keeping folder structure:
   ```
   post.py
   requirements.txt
   .github/workflows/daily-post.yml
   ```

### Add GitHub Secrets
Go to your repo → Settings → Secrets and variables → Actions → New secret:

| Secret name       | Value                                    |
|-------------------|------------------------------------------|
| `GEMINI_API_KEY`  | Your Gemini key from Part A              |
| `MAKE_WEBHOOK_URL`| The webhook URL from Make.com (Part B2)  |

---

## Part D — Test the full flow

1. Go to your GitHub repo → Actions tab
2. Click "Daily AI LinkedIn Post"
3. Click "Run workflow" → "Run workflow"
4. Watch the logs (takes ~30 seconds)
5. Check Make.com → should show execution history
6. Check your LinkedIn profile → post should be live! 🎉

---

## Schedule

Runs daily at **11:30 AM IST** automatically.

To change time, edit `.github/workflows/daily-post.yml`:
```yaml
- cron: "0 6 * * *"   # 06:00 UTC = 11:30 AM IST
```

---

## Cost summary

| Service        | Free tier              | Your usage     |
|----------------|------------------------|----------------|
| GitHub Actions | 2000 min/month         | ~5 min/month   |
| Gemini API     | 1500 requests/day      | 1/day          |
| Make.com       | 1000 operations/month  | ~60/month      |
| LinkedIn       | Always free            | 1 post/day     |
| Image gen      | Python (no API)        | Unlimited      |
| **Total**      | **₹0 forever**         |                |

---

## Troubleshooting

| Problem                        | Fix                                              |
|-------------------------------|--------------------------------------------------|
| Make.com shows no execution   | Check webhook URL is correct in GitHub secrets   |
| LinkedIn post not appearing   | Re-authorize LinkedIn in Make.com connection     |
| Gemini error                  | Check API key is correct in GitHub secrets       |
| Post text looks wrong         | Run manually and check the logs for post preview |
| Make.com "inactive scenario"  | Toggle the scenario ON in Make.com               |
