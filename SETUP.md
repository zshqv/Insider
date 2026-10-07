# Setup Guide

A step-by-step guide to fork Insider and run your own job-sourcing pipeline — no Claude Code required.

---

## 1. Fork and clone

```bash
# Fork on GitHub first (button in top-right), then:
git clone https://github.com/YOUR_USERNAME/Insider.git
cd Insider
python -m venv venv
source venv/bin/activate   # Windows: .\venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Create your `.env`

```bash
cp .env.example .env
```

Open `.env` and fill in your values:

```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
ADZUNA_APP_ID=your_app_id
ADZUNA_APP_KEY=your_api_key
```

### Where to get these

| Secret | How to get it |
|---|---|
| **Discord webhook** | Open your Discord server → channel settings (gear icon) → Integrations → Webhooks → New Webhook → Copy URL |
| **Adzuna API** | Sign up at [developer.adzuna.com](https://developer.adzuna.com/) → Dashboard → your App ID and API Key (free tier: 2,500 calls/month) |

## 3. Customize for your niche

Insider ships configured for entry-level finance roles in India. To adapt it to your own job search, edit these three files:

### `config.json` — target roles

Change the keywords that match against job titles:

```json
{
  "target_roles": [
    "software engineer",
    "frontend developer",
    "backend developer",
    "fullstack",
    "devops"
  ],
  "max_results_per_run": 30
}
```

### `config/filters.yaml` — seniority and location rules

**Seniority** — edit `seniority_block` to control which levels are filtered out:

```yaml
seniority_block:
  - senior
  - staff
  - principal
  - director
  # Remove "manager" if you want manager roles
```

**Noise** — edit `noise_block` to remove non-relevant titles. If you're targeting engineering, remove the engineering entries and add finance/marketing/etc. instead:

```yaml
noise_block:
  - financial analyst
  - accountant
  - bookkeeper
  # Add whatever is noise for YOUR search
```

**Location tiers** — edit to match where you want to work:

```yaml
tier1_locations:
  - san francisco
  - new york

tier2_locations:
  - seattle
  - austin
  - boston
  - worldwide
```

**Remote geo-fence** — controls which "remote" jobs are accepted. Remove countries you'd accept remote work from:

```yaml
remote_region_block:
  - uk
  - germany
  # Remove "us" if you're US-based and want US-remote roles
```

### `config/companies.yaml` — company boards

Add or remove Greenhouse/Lever/Ashby board slugs. The slug is the company identifier in their careers page URL:

- **Greenhouse**: `https://boards.greenhouse.io/SLUG` → use `SLUG`
- **Lever**: `https://jobs.lever.co/SLUG` → use `SLUG`
- **Ashby**: `https://jobs.ashbyhq.com/SLUG` → use `SLUG`

```yaml
greenhouse:
  - google
  - meta
  - netflix

lever:
  - figma
  - notion

ashby:
  - linear
  - vercel
```

### Adzuna categories and countries

Edit `insider/sources/adzuna.py` to change:

```python
CATEGORIES = ["it-jobs"]           # was "accounting-finance-jobs"
COUNTRIES = ["us", "gb", "de"]     # add/remove country codes
```

Available categories: `it-jobs`, `engineering-jobs`, `marketing-jobs`, `healthcare-nursing-jobs`, etc. Country codes: `us`, `gb`, `in`, `de`, `fr`, `au`, `ca`, etc.

## 4. Test locally

```bash
# Dry run — scrapes and prints, no Discord posting
python main.py --dry-run

# Real run — posts to Discord
python main.py --once
```

Check the output:
- **All tiers** appear in your Discord channel with colour-coded embeds
- 🚀 Remote, ⚡ Mumbai, 🌍 International, 🇮🇳 Pan India

## 5. Automate with GitHub Actions

### Add secrets to your fork

Go to your repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**:

| Secret name | Value |
|---|---|
| `DISCORD_WEBHOOK_URL` | Your Discord webhook URL |
| `ADZUNA_APP_ID` | Your Adzuna App ID |
| `ADZUNA_APP_KEY` | Your Adzuna API Key |

### Adjust the schedule

Edit `.github/workflows/sourcing.yml` to change how often it runs:

```yaml
schedule:
  - cron: '*/30 * * * *'    # Every 30 minutes
  # - cron: '0 */2 * * *'   # Every 2 hours
  # - cron: '0 9,18 * * *'  # Twice daily (9 AM and 6 PM UTC)
```

### Enable Actions

Go to your fork → **Actions** tab → click **"I understand my workflows, go ahead and enable them"**.

The pipeline will now run automatically on your schedule.

## 6. Add a new source (optional)

Create `insider/sources/yoursite.py`:

```python
import requests
from insider.sources._common import format_date, within_recency, job


def fetch(filter_fn):
    jobs = []
    try:
        res = requests.get("https://api.example.com/jobs", timeout=10)
        if res.status_code != 200:
            return jobs
        for item in res.json().get("results", []):
            title = item.get("title", "")
            desc = item.get("description", "")

            if not filter_fn(title, desc) or not within_recency(format_date(item.get("date"))):
                continue

            jobs.append(job(
                title=title,
                company=item.get("company", "Unknown"),
                location=item.get("location", "Various"),
                url=item.get("url"),
                source="YourSite",
                job_id=item.get("id"),
                source_type="Aggregator 📦",
                workplace="Remote 🌐",
                is_priority=False,
                date_posted=format_date(item.get("date")),
            ))
    except Exception as e:
        print(f"[!] YourSite fetch failed: {e}")
    return jobs
```

Then register it in `insider/sources/__init__.py`:

```python
from insider.sources.yoursite import fetch as _yoursite

_SOURCES = [
    # ... existing sources ...
    ("YourSite", _yoursite),
]
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `DISCORD_WEBHOOK_URL not set` | Add it to `.env` (local) or GitHub Secrets (Actions) |
| `Adzuna: ADZUNA_APP_ID / ADZUNA_APP_KEY not set; skipping` | Add both to `.env` or GitHub Secrets — Adzuna is optional, the other 6 sources still work |
| `0 new to post` | The dedupe caught them — they were posted in a previous run. Delete `data/seen.json` to reset |
| Jobs from wrong fields showing up | Add those title keywords to `noise_block` in `config/filters.yaml` |
| Too few results | Add more company slugs to `config/companies.yaml` or broaden `tier1_locations` / `india_locations` |
