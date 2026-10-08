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
| **Discord webhook** | See step-by-step guide below |
| **Adzuna API** | Sign up at [developer.adzuna.com](https://developer.adzuna.com/) → Dashboard → your App ID and API Key (free tier: 2,500 calls/month) |

### Creating a Discord webhook (step by step)

1. Open Discord and go to the **server** where you want job alerts
2. Pick the **channel** you want alerts in (or create a new one like `#job-leads`)
3. Click the **gear icon** (⚙️) next to the channel name to open Channel Settings
4. In the left sidebar, click **Integrations**
5. Click **Webhooks**
6. Click **New Webhook**
7. Give it a name (e.g. "Insider Bot") and optionally set an avatar
8. Click **Copy Webhook URL** — this is your `DISCORD_WEBHOOK_URL`
9. Paste it in your `.env` file or add it as a GitHub Actions secret

The URL looks like: `https://discord.com/api/webhooks/1234567890/abcdefg...`

> **Tip:** Don't share this URL publicly — anyone with it can post messages to your channel. If it leaks, delete the webhook and create a new one.

## 3. Set your candidate profile

Edit `config/filters.yaml` under the `candidate:` block to match your situation:

```yaml
candidate:
  german_level: A1            # A1-C2 or "none"
  enrolled_student: false
  needs_visa_sponsorship: true
  based_in: India
  accepts_onsite_in:
    - India
  german_posting_assumes_german_required: true
```

This drives the gate detection — German requirement, enrollment, visa, and location eligibility checks run against these values. See the README for what each gate does.

## 4. Customize for your niche

Insider ships configured for entry-level finance roles in India. To adapt it to your own job search, edit these files:

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

### `config/filters.yaml` — seniority, noise, and location rules

**Seniority** — edit `seniority_block` to control which levels are filtered out.

**Noise** — edit `noise_block` to remove non-relevant titles. The noise block takes precedence over intern/graduate overrides, EXCEPT when the title also contains data, automation, analyst, analytics, operations, finance, or business.

**Location tiers** — edit to match where you want to work.

**Fit rules** — `post_fit_c: false` means Fit C leads (multiple gate failures or no role match) won't be posted to Discord but will still appear in the Google Sheet.

### `config/companies.yaml` — company boards

Add or remove Greenhouse/Lever/Ashby board slugs. The slug is the company identifier in their careers page URL:

- **Greenhouse**: `https://boards.greenhouse.io/SLUG` → use `SLUG`
- **Lever**: `https://jobs.lever.co/SLUG` → use `SLUG`
- **Ashby**: `https://jobs.ashbyhq.com/SLUG` → use `SLUG`

### Adzuna categories and countries

Edit `insider/sources/adzuna.py` to change:

```python
CATEGORIES = ["it-jobs"]           # was "accounting-finance-jobs"
COUNTRIES = ["us", "gb", "de"]     # add/remove country codes
```

## 5. Test locally

```bash
# Dry run — scrapes and prints with fit/gate info, no Discord posting
python main.py --dry-run

# Run tests
python -m pytest tests/ -v

# Real run — posts to Discord
python main.py --once
```

## 6. Set up Google Sheets (optional)

1. Create a new Google Sheet
2. Open **Extensions → Apps Script**
3. Paste the contents of `apps_script/Code.gs`
4. Run `setupSheet()` from the Apps Script editor (it will ask for permissions)
5. Deploy: **Deploy → New deployment → Web app → Execute as: Me, Who has access: Anyone**
6. Copy the deployment URL (ends in `/exec`) — this is your `GOOGLE_SHEET_WEBHOOK`
7. Add it to `.env` (local) or GitHub Secrets (Actions)
8. Set `SHEET_ENABLED=true`

### New columns

The sheet now includes gate and tracking columns. Run **Insider → Ensure Schema** from the sheet menu (or call the web app with a GET request) to add any missing columns.

New pipeline columns: Fit, Gate Pass, German Req, Enrollment Req, Visa, Gate Fail Reasons, Gate Confidence, Date Found.

New tracking columns (you fill these): Date Applied, Follow-up Date, Skip Reason, Contact, Messaged On, Replied?, Notes, Duplicate Flag.

Status options: New, Skipped, Applied, Replied, Interview, Offer, Rejected, Ghosted.

### Auto-fill behavior

- When you set Status to **Applied**, Date Applied and Follow-up Date (+ 7 days) are auto-filled
- Rows stay **Applied** for 21+ days with no reply → auto-marked **Ghosted** (run **Insider → Mark Ghosted** or let the script handle it)

### Migrating an existing sheet

If you already have an older Insider sheet:

```bash
python scripts/migrate_sheet.py --dry-run   # preview changes
python scripts/migrate_sheet.py             # apply changes
```

This adds missing columns without touching existing data. Blank Status cells are set to "New". Existing "Rejected" rows are not changed.

## 7. Automate with GitHub Actions

### Add secrets to your fork

Go to your repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**:

| Secret name | Value |
|---|---|
| `DISCORD_WEBHOOK_URL` | Your Discord webhook URL |
| `ADZUNA_APP_ID` | Your Adzuna App ID |
| `ADZUNA_APP_KEY` | Your Adzuna API Key |
| `GOOGLE_SHEET_WEBHOOK` | Your Apps Script deployment URL |

Set `SHEET_ENABLED=true` as a **repository variable** (not secret) if you want Sheets enabled.

### Adjust the schedule

Edit `.github/workflows/sourcing.yml` to change how often it runs:

```yaml
schedule:
  - cron: '0 * * * *'       # Every hour (default)
  # - cron: '0 */2 * * *'   # Every 2 hours
  # - cron: '0 9,18 * * *'  # Twice daily (9 AM and 6 PM UTC)
```

### Enable Actions

Go to your fork → **Actions** tab → click **"I understand my workflows, go ahead and enable them"**.

The pipeline will now run automatically on your schedule.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `DISCORD_WEBHOOK_URL not set` | Add it to `.env` (local) or GitHub Secrets (Actions) |
| `Adzuna: ADZUNA_APP_ID / ADZUNA_APP_KEY not set; skipping` | Add both to `.env` or GitHub Secrets — Adzuna is optional, the other 6 sources still work |
| `0 new to post` | The dedupe caught them — they were posted in a previous run. Delete `data/seen.json` to reset |
| Jobs from wrong fields showing up | Add those title keywords to `noise_block` in `config/filters.yaml` |
| Too few results | Add more company slugs to `config/companies.yaml` or broaden `tier1_locations` / `india_locations` |
| Sheet version mismatch | Paste the latest `apps_script/Code.gs` into the editor and deploy a **new version**. The pipeline will also post a Discord warning when it detects a version mismatch. |
| Gate results all Unknown | Make sure sources are returning descriptions — check the source API responses |
