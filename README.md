# Insider

An automated job-sourcing pipeline that scrapes 7 sources every hour, filters for entry-level roles, gates on eligibility (German, visa, enrollment, location), and delivers leads to Discord and Google Sheets.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Automation: GitHub Actions](https://img.shields.io/badge/automation-GitHub%20Actions-2088FF.svg)](./.github/workflows/sourcing.yml)

---

## Quick peek

### Discord alerts

Every new lead lands in your Discord channel with a tier badge, fit grade, gate status, and a direct apply link.

![Discord embed](assets/discord-embed.png)

### Google Sheets tracker

All leads are logged to a Google Sheet with dark theme formatting, status dropdowns, gate columns, fit grades, follow-up tracking, and auto-ghosting after 3 weeks of no activity.

![Google Sheet tracker](assets/google-sheet.png)

---

## How it works

1. **Scrape** — Fetches jobs from 7 sources (54+ company boards + 4 aggregators)
2. **Filter** — Matches against your target roles, blocks senior/noise titles, enforces a YOE cap
3. **Classify** — Assigns a priority tier based on location
4. **Gate** — Checks German requirement, enrollment, visa sponsorship, and location eligibility
5. **Grade** — Assigns Fit A/B/C based on gate results and role match
6. **Dedupe** — Checks against `data/seen.json` so you never get the same job twice
7. **Deliver** — Posts new leads to Discord (Fit A and B by default), logs all to Google Sheets

```
Sources (7)                     Pipeline                       Sinks
───────────                     ────────                       ─────
Greenhouse (34 boards)  ──┐     Role keyword match      ┌───→ Discord
Lever (10 boards)       ──┤     Seniority block         │     fit/gate-coded embeds
Ashby (10 boards)       ──┤     Noise exclusion         │     (Fit C skipped by default)
Remotive                ──┼──→  YOE cap (≤ 2)       ──→ │
Arbeitnow               ──┤     Tier classification     ├───→ Google Sheets (optional)
WeWorkRemotely          ──┤     Gate detection          │     status tracking, follow-ups
Adzuna (IN + GB)        ──┘     Fit grading (A/B/C)     │     duplicate flagging
                                Cross-run dedupe        └───→ All tiers + fits logged
```

---

## Candidate config and gates

Set your profile in `config/filters.yaml` under the `candidate:` block:

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

### Gate checks

| Gate | What it checks | Pass | Fail |
|---|---|---|---|
| **German** | Parses explicit levels (B2, C1) and phrases ("fließend", "fluent German"). Soft markers ("von Vorteil", "nice to have") don't fail. German-language postings auto-fail if your level can't cover it. | Your level meets the requirement, or it's soft | Hard requirement exceeds your level |
| **Enrollment** | Detects Werkstudent, working student, Pflichtpraktikum, "currently enrolled" | You're enrolled, or no enrollment needed | Requires enrollment and you're not enrolled |
| **Visa** | Looks for "no sponsorship", "must have right to work" vs "visa sponsorship available", "relocation" | Sponsorship offered, or you don't need it | No sponsorship and you need it |
| **Location** | Reuses the tier system; remote = Pass, on-site in your accepted locations = Pass | Remote or in your accepted locations | On-site abroad without relocation offered |

### Fit grades

| Grade | Meaning |
|---|---|
| **A** | All gates pass + title matches your target roles |
| **B** | Exactly one gate fails + title matches, or any gate is Unknown |
| **C** | Everything else (multiple fails or no role match) |

### Worked example

**Job:** "Junior Financial Analyst" at Stripe, Remote — Worldwide.
Description mentions "visa sponsorship available", no German requirement, not a student role.

- German gate: Pass (no requirement found)
- Enrollment gate: Pass (no student keywords)
- Visa gate: Pass ("visa sponsorship available")
- Location gate: Pass (tier 0, genuinely remote)
- **Gate Pass: Pass** → **Fit: A** (all gates pass + "analyst" matches target roles)

---

## Tier system

| Tier | Badge | Criteria | Example |
|---|---|---|---|
| **High Priority** | Remote | Genuinely remote — worldwide or India, no western geo-fence | "Remote — Worldwide" |
| **Tier 1** | Mumbai | Mumbai — commutable | "Mumbai, Maharashtra" |
| **Tier 2** | International | Global on-site or geo-fenced remote (US, UK, EU) | "London, UK" |
| **Tier 3** | Pan India | Rest of India on-site | "Bangalore, Karnataka" |

Internships with conversion/PPO signals get a badge.

---

## Sheet columns

| Column | Source | Description |
|---|---|---|
| Date Posted | API | Real posted date from source (blank if unavailable) |
| Title | API | Job title |
| Company | API | Company name |
| Location | API | Location string |
| Source | Pipeline | Which source found it |
| URL | API | Apply link (displayed as "Open" hyperlink) |
| Workplace | Pipeline | Remote / Hybrid / On-site |
| Tier | Pipeline | Location tier |
| Fit | Pipeline | A / B / C grade |
| Gate Pass | Pipeline | Pass / Fail / Unknown |
| German Req | Pipeline | Required German level (if any) |
| Enrollment Req | Pipeline | Yes / No / Unknown |
| Visa | Pipeline | Yes / No / Unknown |
| Gate Fail Reasons | Pipeline | Short explanation of failures |
| Gate Confidence | Pipeline | Full text / Snippet only / Title only |
| Date Found | Pipeline | When the pipeline first saw this job |
| Status | You | New / Skipped / Applied / Replied / Interview / Offer / Rejected / Ghosted |
| Date Applied | Auto/You | Auto-filled when Status → Applied |
| Follow-up Date | Auto | Date Applied + 7 days |
| Skip Reason | You | Why you skipped this lead |
| Contact | You | LinkedIn URL of recruiter/hiring manager |
| Messaged On | You | Date you messaged the contact |
| Replied? | You | Whether they replied |
| Notes | You | Free-form notes |
| Duplicate Flag | Pipeline | "Same role as row N" or "Same company: N roles" |

---

## How to use

### 1. Fork and clone

```bash
git clone https://github.com/YOUR_USERNAME/Insider.git
cd Insider
python -m venv venv
source venv/bin/activate   # Windows: .\venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # fill in your keys
```

### 2. Configure your secrets

| Variable | Required | Where to get it |
|---|---|---|
| `DISCORD_WEBHOOK_URL` | Yes | Channel settings → Integrations → Webhooks |
| `ADZUNA_APP_ID` | No | [developer.adzuna.com](https://developer.adzuna.com/) (free) |
| `ADZUNA_APP_KEY` | No | Adzuna source skipped if not set |
| `SHEET_ENABLED` | No | Set to `true` to enable Google Sheets |
| `GOOGLE_SHEET_WEBHOOK` | No | Apps Script web app URL (see `apps_script/Code.gs`) |

### 3. Customize for your search

Edit these files — no code changes needed:

- **`config.json`** — target role keywords (what job titles to match)
- **`config/filters.yaml`** — seniority rules, noise exclusions, location tiers, candidate profile, fit rules
- **`config/companies.yaml`** — Greenhouse/Lever/Ashby board slugs

### 4. Run

```bash
python main.py --dry-run    # scrape + print, no posting
python main.py --once       # real run — posts to Discord + Sheets
```

### 5. Automate with GitHub Actions

Add your secrets under **Settings → Secrets and variables → Actions**, and the included workflow runs every hour automatically.

For the full walkthrough, see **[SETUP.md](./SETUP.md)**.

---

## Adapt Insider with AI

Don't have Claude Code? Copy this prompt into any AI assistant (Claude, ChatGPT, etc.) to get help customising Insider for your niche:

<details>
<summary>Click to expand prompt</summary>

```
I forked the Insider job-sourcing pipeline (https://github.com/zshqv/Insider).
It scrapes 7 job board APIs, filters by role/seniority/location, gates on
eligibility (German, visa, enrollment, location), and posts matching jobs
to Discord.

Help me customise it for my job search. Here's what I'm looking for:

- Roles: [e.g. "software engineer", "data scientist", "product manager"]
- Seniority: [e.g. "entry-level only", "mid-level", "any"]
- Locations I want (Tier 1 priority): [e.g. "San Francisco", "New York"]
- Other acceptable locations (Tier 2): [e.g. "Seattle", "Austin", "Remote US"]
- Industries/fields to EXCLUDE from results: [e.g. "finance", "healthcare"]
- German level: [e.g. "none", "B1", "C1"]
- Enrolled student: [yes/no]
- Need visa sponsorship: [yes/no]
- Based in: [country]

Based on this, generate:
1. An updated config.json with my target roles
2. An updated config/filters.yaml with my candidate profile, seniority rules,
   noise exclusions, and location tiers
3. An updated config/companies.yaml with relevant company board slugs
4. Any changes needed in insider/sources/adzuna.py (categories and countries)
```

</details>

---

## Job boards

| Source | Type | Account needed? | What it scrapes |
|---|---|---|---|
| Greenhouse | Direct career portal | No — public API | 34 company boards (Stripe, Razorpay, Coinbase, etc.) |
| Lever | Direct career portal | No — public API | 10 company boards |
| Ashby | Direct career portal | No — public API | 10 company boards |
| Remotive | Aggregator | No — public API | Remote finance/legal jobs |
| Arbeitnow | Aggregator | No — public API | EU + global jobs |
| WeWorkRemotely | Aggregator | No — public RSS | Remote finance/legal feed |
| Adzuna | Aggregator | Yes — free account ([sign up](https://developer.adzuna.com/)) | India + GB finance jobs (2,500 calls/mo free) |

**6 out of 7 sources need zero signup.** Only Adzuna requires a free developer account — and it's optional, the pipeline runs fine without it.

---

## Schedule

| What | When |
|---|---|
| Pipeline runs | Every hour via GitHub Actions cron |
| Dedupe retention | 180 days (seen jobs auto-expire) |
| Auto-ghost (Sheets) | 21 days after Date Applied with no reply → marked Ghosted |
| Recency window | Last 30 days (older job postings are skipped) |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      GitHub Actions (cron)                       │
│                         every hour                               │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                    python main.py --once
                           │
          ┌────────────────▼────────────────┐
          │         Source Registry          │
          │   insider/sources/__init__.py    │
          │                                 │
          │  Greenhouse ─── 34 boards       │
          │  Lever ──────── 10 boards       │
          │  Ashby ──────── 10 boards       │
          │  Remotive ───── finance/legal   │
          │  Arbeitnow ──── EU/global       │
          │  WWR ────────── remote RSS      │
          │  Adzuna ─────── IN + GB         │
          └────────────────┬────────────────┘
                           │
          ┌────────────────▼────────────────┐
          │         Filter Pipeline          │
          │     insider/filters.py           │
          │                                 │
          │  1. Role keyword match           │
          │  2. Seniority block              │
          │  3. Noise block (+ override)     │
          │  4. YOE cap (≤ 2 years)          │
          │  5. Tier classification           │
          └────────────────┬────────────────┘
                           │
          ┌────────────────▼────────────────┐
          │         Gate Detection           │
          │     insider/gates.py             │
          │                                 │
          │  1. German requirement           │
          │  2. Enrollment required           │
          │  3. Visa sponsorship             │
          │  4. Location eligibility          │
          │  5. Fit grading (A/B/C)          │
          └────────────────┬────────────────┘
                           │
          ┌────────────────▼────────────────┐
          │           Dedupe                 │
          │     insider/dedupe.py            │
          │                                 │
          │  data/seen.json (Actions cache)  │
          │  Key: source:id + url:normalized │
          │  Retention: 180 days             │
          └────────────────┬────────────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
    ┌─────────▼─────────┐    ┌─────────▼─────────┐
    │    Discord Sink    │    │  Google Sheets     │
    │                    │    │  (optional)        │
    │  Fit/gate-coded    │    │  Apps Script v4    │
    │  embeds            │    │  Gate columns      │
    │  Fit C skipped     │    │  Status tracking   │
    │  (configurable)    │    │  Follow-up dates   │
    │  Rate-limit aware  │    │  Duplicate flags   │
    └────────────────────┘    └────────────────────┘
```

---

## Project structure

```
├── main.py                    Entry point
├── config.json                Target roles, locations, limits
├── config/
│   ├── companies.yaml         Company boards (Greenhouse/Lever/Ashby slugs)
│   └── filters.yaml           Seniority rules, tiers, candidate profile, fit rules
├── insider/
│   ├── sources/               One module per source (7 total)
│   ├── filters.py             Role filter + tier classifier
│   ├── gates.py               Gate detection + fit grading
│   ├── dedupe.py              Cross-run deduplication (data/seen.json)
│   ├── sinks/sheet.py         Google Sheets sink
│   └── util.py                Env helpers, secret redaction
├── apps_script/Code.gs        Google Sheets webhook receiver (v4)
├── scripts/migrate_sheet.py   One-time sheet migration
├── tests/                     pytest test suite
├── assets/                    Screenshots for README
├── .env.example               Template for local secrets
└── .github/workflows/         GitHub Actions cron
```

---

## License

MIT © [ashu](./LICENSE)

---

Need help setting this up or have questions? Open an issue or email `YOUR_EMAIL`.
