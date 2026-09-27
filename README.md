# 🕵️ Insider — Open-Source Job Lead Scraper

> An automated, multi-source job-sourcing engine that hunts down roles matching *your* criteria — any niche, any seniority — and delivers clean leads straight to Discord and Google Sheets. No manual job-board scrolling required.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![Automation: GitHub Actions](https://img.shields.io/badge/automation-GitHub%20Actions-2088FF.svg)](./.github/workflows/sourcing.yml)

---

## ✨ What is Insider?

Insider is a lightweight, config-driven pipeline that:

- 🔎 **Pulls jobs** from multiple public job APIs (Arbeitnow, Remotive, Jobicy)
- 🧹 **Filters** them down to exactly what you're looking for — role, location, seniority
- 🔁 **Deduplicates** leads across sources
- 📬 **Delivers** clean, formatted results to **Discord** (via webhook) and **Google Sheets** (as a lightweight CRM)
- ⏰ **Runs on autopilot** every 30 minutes via GitHub Actions — or locally, on your own schedule

It ships pre-configured for early-career finance roles, but the whole point of Insider is that it's **not locked to finance** — swap the config and a couple of filter lists, and it becomes a lead-gen engine for design roles, engineering roles, marketing, sales, whatever you're hunting for. See [Adapting Insider to Your Niche](#-adapting-insider-to-your-niche) below.

---

## 🏗️ How It Works

┌──────────────────────────────────────────────────┐
│ Multi-Source Data Extraction │
│ (Arbeitnow API · Remotive API · Jobicy) │
└────────────────────────┬───────────────────────────┘
│
▼
┌──────────────────────────────────────────────────┐
│ Filtering, Matching & Deduplication │
│ • Role & keyword matching │
│ • Location matching │
│ • Seniority / niche exclusions │
└────────────────────────┬───────────────────────────┘
│
┌────────────┴────────────┐
▼ ▼
┌───────────────────┐ ┌────────────────────────┐
│ 💬 Discord │ │ 📊 Google Sheets │
│ Clean embed cards │ │ Auto-updating tracker │
└───────────────────┘ └────────────────────────┘


---

## 🚀 Quickstart

### 1. Clone & set up your environment

```bash
git clone https://github.com/zshqv/Insider.git
cd Insider
python -m venv venv
source venv/bin/activate   # Windows: .\venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure your search

Run the interactive setup:

```bash
python setup.py
```

This walks you through target roles, locations, seniority, and your webhook URLs, and writes it all to `config.json`.

> ⚠️ **Don't commit real webhook URLs to `config.json` if your repo is public.** Use environment variables (`DISCORD_WEBHOOK_URL`, `GOOGLE_SHEET_WEBHOOK`) instead, or keep a local `config.json` out of version control.

### 3. Run it

```bash
python main.py --once      # single run
python main.py             # continuous loop, checks every N hours
```

### 4. (Optional) Automate it with GitHub Actions

The included workflow (`.github/workflows/sourcing.yml`) runs the pipeline every 30 minutes in the cloud — no machine needs to stay on. Just add your webhook URLs as **repo secrets**.

---

## ⚙️ Configuration Reference (`config.json`)

```json
{
  "target_roles": ["finance", "financial analyst", "fp&a", "treasury"],
  "target_locations": ["remote", "germany", "united kingdom", "india"],
  "experience_level": ["entry-level", "junior", "internship"],
  "discord_webhook_url": "",
  "google_sheet_webhook": "",
  "check_interval_hours": 0.5,
  "max_results_per_run": 25
}
```

| Field | What it does |
|---|---|
| `target_roles` | Keywords matched against job titles |
| `target_locations` | Keywords matched against job location strings |
| `experience_level` | Documented for reference — see note below |
| `discord_webhook_url` | Where lead cards get posted |
| `google_sheet_webhook` | Apps Script endpoint for your tracker sheet |
| `check_interval_hours` | How often the loop re-checks (in continuous mode) |
| `max_results_per_run` | Cap on leads processed per run |

---

## 🎯 Adapting Insider to Your Niche

Insider ships tuned for **early-career finance roles** by default, but it's built to be repointed. Two layers control what gets through:

1. **`config.json`** — your keywords and locations. Editable without touching code.
2. **`scraper.py`** — the exclusion filters and source-API categories, which are currently hardcoded for the finance use case:
   - `seniority_exclusions` — currently strips out Senior/Lead/Director/Manager titles (i.e., entry-level only). Edit or remove this list if you want a different seniority band.
   - `tech_exclusions` — currently strips out engineering-adjacent titles. Remove or replace this if your niche *is* engineering.
   - The Remotive and Jobicy fetch calls query `category=finance-legal` and `industry=finance` — change these query params to match your target industry.

If you're repointing Insider at a new niche, start there — `config.json` gets you keyword/location targeting, `scraper.py` gets you the category and seniority logic.

---

## 🗺️ Roadmap

- [x] Multi-source ingestion (Arbeitnow, Remotive, Jobicy)
- [x] Discord embed delivery with workplace-type detection
- [x] Google Sheets CRM append with clickable links
- [ ] Generalize exclusion filters and source categories via `config.json` (remove finance hardcoding)
- [ ] Add LinkedIn, Indeed, Greenhouse, Lever, Adzuna as additional sources
- [ ] Optional LLM scoring layer to rank leads by relevance to a candidate profile

---

## 🤝 Contributing

Pull requests welcome — especially around generalizing the filtering logic, adding new job sources, or improving the CRM integrations. Open an issue first for larger changes.

---

## 📄 License

MIT © [ashu](./LICENSE) — free to use, modify, and distribute.