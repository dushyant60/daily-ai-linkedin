# Daily AI LinkedIn Post

An automated system that posts daily AI news summaries to your personal LinkedIn profile using GitHub Actions, OpenRouter AI, and Make.com. 100% free with no company page required.

## 🚀 Overview

**Workflow:**
- GitHub Actions (free) → fetches AI news from RSS feeds
- Generates engaging post with OpenRouter (free tier)
- Creates custom image with Unsplash photo + overlay
- Uploads image to imgbb (free)
- Sends post + image URL to Make.com webhook
- Make.com posts to your LinkedIn personal profile

**Required API Keys:**
- OpenRouter API key (free)
- Make.com webhook URL
- Unsplash Access Key (free)
- ImgbB API key (free)

## ✨ Features

- **Automated AI News Aggregation**: Parses multiple RSS feeds for latest AI headlines
- **AI-Generated Content**: Creates professional LinkedIn posts using OpenRouter
- **Custom Image Generation**: Fetches relevant images from Unsplash and adds branded overlays
- **Safety Filters**: Built-in content moderation to ensure appropriate posts
- **Daily Scheduling**: Runs automatically at 11:30 AM IST via GitHub Actions
- **100% Free**: No paid services required

## 📋 Prerequisites

- GitHub account (free)
- Make.com account (free tier: 1000 operations/month)
- OpenRouter account (free tier available)
- Unsplash Developer account (free)
- ImgbB account (free)

## 🛠️ Installation & Setup

### Step 1: Get API Keys

#### OpenRouter API Key
1. Go to [https://openrouter.ai/](https://openrouter.ai/)
2. Sign up for a free account
3. Navigate to API Keys section
4. Create a new key (free tier: 1000 tokens/day)

#### Unsplash Access Key
1. Go to [https://unsplash.com/developers](https://unsplash.com/developers)
2. Create a new app
3. Copy the "Access Key"

#### ImgbB API Key
1. Go to [https://imgbb.com/](https://imgbb.com/)
2. Sign up for a free account
3. Go to API section and copy your API key

### Step 2: Set up Make.com Scenario

1. Create a free account at [https://make.com](https://make.com)
2. Click "Create a new scenario"
3. Import the provided blueprint: `Integration Webhooks, LinkedIn.blueprint.json`
4. Or manually create:
   - Add **Custom Webhook** module (name: "LinkedIn Post Trigger")
   - Add **LinkedIn → Create a Post** module
   - Connect your LinkedIn account (personal profile)
   - Configure post fields:
     - Visibility: PUBLIC
     - Commentary: `{{1.post_text}}`
     - Media: `{{1.image_url}}` (if using image)

5. Copy the webhook URL from the webhook module

### Step 3: Set up GitHub Repository

1. Create a **private** repository on GitHub
2. Upload these files:
   ```
   post.py
   requirements.txt
   .github/workflows/daily-post.yml
   README.md
   ```

#### Add GitHub Secrets
Go to repository Settings → Secrets and variables → Actions → New repository secret:

| Secret Name          | Value                          |
|----------------------|--------------------------------|
| `OPENROUTER_API_KEY` | Your OpenRouter API key        |
| `MAKE_WEBHOOK_URL`   | Webhook URL from Make.com      |
| `UNSPLASH_ACCESS_KEY`| Your Unsplash Access Key       |
| `IMGBB_API_KEY`      | Your ImgbB API key             |

### Step 4: Configure Workflow Schedule

Edit `.github/workflows/daily-post.yml` to set your preferred time:

```yaml
- cron: "0 6 * * *"   # 06:00 UTC = 11:30 AM IST
```

## 🚀 Usage

### Manual Test Run
1. Go to your GitHub repo → Actions tab
2. Click "Daily AI LinkedIn Post" workflow
3. Click "Run workflow" → "Run workflow"
4. Monitor the logs (takes ~30-60 seconds)
5. Check Make.com for execution history
6. Verify post appears on your LinkedIn profile

### Automatic Daily Posts
The workflow runs automatically according to the cron schedule. No intervention required.

## 📁 Project Structure

```
├── post.py                    # Main Python script
├── requirements.txt           # Python dependencies
├── Integration Webhooks, LinkedIn.blueprint.json  # Make.com scenario export
├── .github/workflows/daily-post.yml              # GitHub Actions workflow
└── README.md                  # This file
```

## 🔧 How It Works

1. **News Fetching**: Parses RSS feeds from TechCrunch, VentureBeat, AI News, etc.
2. **Content Generation**: Uses OpenRouter to create engaging LinkedIn posts
3. **Image Creation**: Fetches Unsplash photos and adds branded overlays
4. **Image Upload**: Uploads to ImgbB for public URL
5. **Posting**: Sends data to Make.com webhook for LinkedIn posting

## 💰 Cost Breakdown

| Service          | Free Tier              | Usage          |
|------------------|------------------------|----------------|
| GitHub Actions   | 2000 min/month         | ~5 min/month   |
| OpenRouter       | Free tier available    | 1 request/day  |
| Make.com         | 1000 operations/month  | ~60/month      |
| Unsplash         | 50 requests/hour       | 1 request/day  |
| ImgbB            | Free tier              | 1 upload/day   |
| LinkedIn         | Always free            | 1 post/day     |
| **Total**        | **₹0 forever**         |                |

## 🐛 Troubleshooting

| Issue                          | Solution                                      |
|--------------------------------|-----------------------------------------------|
| Make.com shows no execution    | Verify webhook URL in GitHub secrets          |
| LinkedIn post not appearing    | Re-authorize LinkedIn in Make.com             |
| OpenRouter error               | Check API key and free tier limits            |
| Image upload fails             | Verify ImgbB API key                          |
| Workflow fails                 | Check GitHub Actions logs for error details   |
| Make.com "inactive scenario"   | Toggle scenario ON in Make.com                |
| Unsplash API limit             | Wait or upgrade Unsplash plan                 |

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is open source. Feel free to use and modify.

## 🙏 Acknowledgments

- OpenRouter for AI content generation
- Unsplash for beautiful stock photos
- ImgbB for free image hosting
- Make.com for automation platform
- GitHub Actions for CI/CD

---

**Made with ❤️ for the AI community**
