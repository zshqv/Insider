# Insider

Automated job-sourcing pipeline that scrapes 7 sources, filters for entry-level / intern roles, and delivers leads to Discord and Google Sheets.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Automation: GitHub Actions](https://img.shields.io/badge/automation-GitHub%20Actions-2088FF.svg)](./.github/workflows/sourcing.yml)

---

## How it works

```
Sources (7)                     Filters                        Sinks
───────────                     ───────                        ─────
Greenhouse (34 boards)  ──┐     Role keyword match      ┌───→ Discord (Tier 1 + 2)
Lever (10 boards)       ──┤     Seniority block         │     embeds with tier badges
Ashby (10 boards)       ──┤     Noise exclusion         │
Remotive                ──┼──→  YOE cap (≤ 2)       ──→ ├───→ Google Sheets (optional)
Arbeitnow               ──┤     Geo-fence detection     │     auto-updating tracker
WeWorkRemotely          ──┤     Tier classification     │
Adzuna (IN + GB)        ──┘     Cross-run dedupe        └───→ data/tier3.jsonl (Tier 3)
```

## Discord preview

![Discord embed](assets/discord-embed.png)

## Tier system

| Tier | Criteria | Destination |
|---|---|---|
| **Tier 1** ⚡ | Mumbai **or** genuinely fully-remote (no geo-fence) | Discord + Sheet |
| **Tier 2** 🌐 | Other India cities, Worldwide | Discord + Sheet |
| **Tier 3** 📁 | Everything else (US, EU, LATAM, etc.) | `data/tier3.jsonl` only |

Internships with conversion/PPO signals get a 🎓 badge on the Discord card.

## Quickstart

```bash
git clone https://github.com/zshqv/Insider.git
cd Insider
python -m venv venv
source venv/bin/activate   # Windows: .\venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # fill in your keys
```

### Required secrets (`.env` locally, repo secrets in Actions)

| Variable | Required | Notes |
|---|---|---|
| `DISCORD_WEBHOOK_URL` | Yes | Channel settings → Integrations → Webhooks |
| `ADZUNA_APP_ID` | No | [developer.adzuna.com](https://developer.adzuna.com/) |
| `ADZUNA_APP_KEY` | No | Adzuna source is skipped if not set |
| `SHEET_ENABLED` | No | Set to `true` to enable Google Sheets sink |
| `GOOGLE_SHEET_WEBHOOK` | No | Apps Script web app URL (see `apps_script/Code.gs`) |

### Run

```bash
python main.py --once       # single run
python main.py --dry-run    # scrape + print, no posting
```

### GitHub Actions

The included workflow runs twice daily (11 AM and 7 PM IST). Add your secrets under **Settings → Secrets and variables → Actions**.

## Project structure

```
├── main.py                    Entry point
├── config.json                Target roles, locations, limits
├── config/
│   ├── companies.yaml         Company boards (Greenhouse/Lever/Ashby slugs)
│   └── filters.yaml           Seniority rules, tiers, geo-fence, badges
├── insider/
│   ├── sources/               One module per source (7 total)
│   ├── filters.py             Role filter + tier classifier
│   ├── dedupe.py              Cross-run deduplication (data/seen.json)
│   ├── sinks/sheet.py         Google Sheets sink
│   └── util.py                Env helpers, secret redaction
├── apps_script/Code.gs        Google Sheets webhook receiver
├── assets/                    Screenshots for README
├── .env.example               Template for local secrets
└── .github/workflows/         GitHub Actions cron
```

## Customisation

**Change target roles** → edit `config.json` `target_roles` list.

**Add/remove company boards** → edit `config/companies.yaml`.

**Adjust seniority / location rules** → edit `config/filters.yaml`. All filter logic is config-driven, no code changes needed.

**Add a new source** → create `insider/sources/yoursite.py` with a `fetch(filter_fn)` function, register it in `insider/sources/__init__.py`.

## License

MIT © [ashu](./LICENSE)
