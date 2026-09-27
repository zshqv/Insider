# 💼 Insider Career Intelligence Engine

> An automated, multi-source job ingestion pipeline designed to hunt for early-career corporate finance, FP&A, audit, risk, and analytics roles globally. Operates on cloud workflows, delivering filtered job leads to Discord and Google Sheets.

---

## 🎯 Scope & Core Focus

The engine is tuned to capture early-career finance roles while filtering out market-facing noise and senior positions:
* **Included Domains:** Corporate Finance, FP&A, Treasury, M&A, Financial Operations, Credit Analysis, Deal Desk, Audit, and Financial Data Analytics.
* **Excluded Noise:** Senior/Lead/Director titles, general software engineering, and public market/trading roles (Trader, Execution, Market Maker, FX, Algo Trading).
* **Target Regions:** Global Remote, EU Financial Hubs (Frankfurt, Zurich, Paris, Amsterdam, London, Dublin, Luxembourg), APAC (Singapore, Tokyo, Seoul, Hong Kong), India, and North America.

---

## 🏗️ Architecture & Pipeline

┌─────────────────────────────────────────────────────────┐
│              Multi-Source Data Extraction               │
│         (Arbeitnow API | Remotive API | Jobicy API)     │
└───────────────────────────┬─────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────┐
│            Strict Filtering & Deduplication             │
│   • Negative Keyword Exclusions (Seniority & Tech)     │
│   • Market/Trading Role Filtering                       │
│   • Workplace Model Detection (Remote / Hybrid / On-site)│
└───────────────────────────┬─────────────────────────────┘
│
┌───────────────┴───────────────┐
▼                               ▼
┌───────────────────────┐       ┌───────────────────────┐
│   Discord Webhook     │       │ Google Apps Script    │
│   Clean Embed Cards   │       │ Dark-Mode Tracker CRM │
└───────────────────────┘       └───────────────────────┘


---

## 🚀 Quickstart (Local Execution)

1. **Clone & Setup Environment:**
   ```bash
   git clone [https://github.com/your-username/Insider.git](https://github.com/your-username/Insider.git)
   cd Insider
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   pip install requests
Configure Webhooks (config.json):
Ensure your webhooks are present in config.json or exported as environment variables (DISCORD_WEBHOOK_URL and GOOGLE_SHEET_WEBHOOK).

Run Pipeline Manual Execution:

PowerShell
python main.py --once
⚙️ Configuration Schema (config.json)
JSON
{
  "target_roles": [
    "finance", "financial analyst", "corporate finance", "fp&a", 
    "treasury", "m&a", "audit", "accounting", "credit analyst", 
    "business analyst", "data analyst", "deal desk"
  ],
  "target_locations": [
    "remote", "germany", "switzerland", "united kingdom", "india", 
    "united states", "japan", "korea", "singapore", "hong kong", 
    "luxembourg", "netherlands", "france", "ireland"
  ],
  "experience_level": ["entry-level", "junior", "internship"],
  "check_interval_hours": 0.5,
  "max_results_per_run": 25
}
🗺️ Roadmap & Next Steps
[x] Multi-source ingestion (Arbeitnow, Remotive, Jobicy).

[x] Clean Discord embed output with Workplace Type detection.

[x] Direct Google Sheets CRM append with hyperlink formatting.

[ ] Expand Ingestion Sources: Integrate dynamic scrapers/APIs for LinkedIn, Indeed, Greenhouse, Lever, and Adzuna to scale lead volume.

[ ] AI Match Scoring: Add an LLM layer to evaluate role relevance against custom candidate profiles.