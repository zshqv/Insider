import sys
import time
import json
import argparse
import requests
from dotenv import load_dotenv
from insider.sources import fetch_all
from insider.filters import build_role_filter, classify_tier
from insider.sinks.sheet import SheetClient, SheetError
from insider.dedupe import SeenStore
from insider.util import env, redact

def load_config(config_path="config.json"):
    with open(config_path, "r") as f:
        config = json.load(f)

    # Secrets come only from the environment (.env locally, repo secrets in Actions).
    load_dotenv()
    config["discord_webhook_url"] = env("DISCORD_WEBHOOK_URL")
    config["google_sheet_webhook"] = env("GOOGLE_SHEET_WEBHOOK")
    config["sheet_enabled"] = (env("SHEET_ENABLED") or "").lower() == "true"
    return config

def send_to_discord(job, webhook_url):
    """Returns True only if Discord accepted the message."""

    tier = job.get("tier", 2)
    _TIER_COLORS = {0: 0x10B981, 1: 0xF59E0B, 2: 0x8B5CF6, 3: 0x3B82F6}
    _TIER_BADGES = {
        0: "🚀 **HIGH PRIORITY — REMOTE**",
        1: "⚡ **TIER 1 — MUMBAI**",
        2: "🌍 **TIER 2 — INTERNATIONAL**",
        3: "🇮🇳 **TIER 3 — PAN INDIA**",
    }
    color = _TIER_COLORS.get(tier, 0x3B82F6)
    tier_badge = _TIER_BADGES.get(tier, "🌐 **TIER 2**")
    ppo = job.get("badge", "")
    if ppo:
        tier_badge += f"\n🎓 {ppo}"
    date_posted = job.get("date_posted", "Recently")

    embed = {
        "title": f"💼 {job['title']}",
        "description": (
            f"{tier_badge}\n\n"
            f"**Company:** `{job.get('company', 'N/A')}`\n"
            f"**Location:** `{job.get('location', 'N/A')}`\n"
            f"**Date Posted:** `{date_posted}`"
        ),
        "color": color,
        "fields": [
            {"name": "📍 Workplace", "value": f"`{job.get('workplace_type', 'N/A')}`", "inline": True},
            {"name": "📡 Source", "value": f"`{job.get('source', 'N/A')}`", "inline": True},
            {"name": "🔗 Application", "value": f"[**Apply directly on {job.get('source', 'Portal')} ↗**]({job.get('url')})", "inline": False}
        ],
        "footer": {
            "text": f"Career Intelligence Pipeline • Ingested {date_posted}"
        }
    }

    for attempt in range(3):
        try:
            res = requests.post(webhook_url, json={"embeds": [embed]}, timeout=10)
            if res.status_code == 429:
                # Webhooks allow ~5 requests per 2 seconds; wait as long as Discord asks.
                retry_after = float(res.json().get("retry_after", 2))
                time.sleep(min(retry_after, 30))
                continue
            res.raise_for_status()
        except Exception as e:
            print(f"[!] Failed to send job to Discord: {redact(e, webhook_url)}")
            return False
        print(f"[✔] Discord alert sent for: {job.get('title')}")
        return True
    print(f"[!] Discord still rate-limiting after retries; will retry next run: {job.get('title')}")
    return False

def to_sheet_lead(job):
    return {
        "date_posted": job.get("date_posted"),
        "title": job.get("title"),
        "company": job.get("company"),
        "location": job.get("location"),
        "source": job.get("source"),
        "url": job.get("url"),
        "workplace": job.get("workplace_type"),
        "tier": _TIER_LABELS.get(job.get("tier"), "Tier 2 🌐"),
    }

def send_to_google_sheet(jobs, webhook_url):
    """Optional sink: never raises, so a Sheet problem can't fail the run."""
    if not webhook_url:
        print("[!] SHEET_ENABLED is true but GOOGLE_SHEET_WEBHOOK is not set; skipping Google Sheet.")
        return
    if not jobs:
        return

    try:
        results = SheetClient(webhook_url).append([to_sheet_lead(j) for j in jobs])
    except SheetError as e:
        print(f"[!] Google Sheet logging FAILED for all {len(jobs)} lead(s): {e}")
        return
    except Exception as e:
        print(f"[!] Google Sheet logging FAILED unexpectedly: {redact(e, webhook_url)}")
        return

    counts = {}
    for job, result in zip(jobs, results):
        status = result.get("status")
        counts[status] = counts.get(status, 0) + 1
        if status == "error":
            print(f"[!] Sheet rejected '{job.get('title')}': {result.get('message')}")
    print(f"[*] Google Sheet: {counts.get('ok', 0)} added, {counts.get('duplicate', 0)} already present, "
          f"{counts.get('error', 0)} failed.")

_TIER_LABELS = {0: "Remote 🚀", 1: "Mumbai ⚡", 2: "International 🌍", 3: "Pan India 🇮🇳"}


def run_pipeline(dry_run=False):
    config = load_config()
    filter_fn = build_role_filter(config.get("target_roles", []))
    seen = SeenStore()

    print("[*] Starting Job Ingestion Pipeline Execution...")
    jobs, counts = fetch_all(filter_fn)
    source_summary = ", ".join(f"{name}: {n}" for name, n in counts.items())

    for j in jobs:
        classify_tier(j)

    by_tier = {}
    for j in jobs:
        by_tier.setdefault(j.get("tier"), []).append(j)

    postable = [j for j in jobs if not seen.is_seen(j)]
    def _sort_key(j):
        tier = j.get("tier", 9)
        date = j.get("date_posted", "0000-00-00")
        date_inv = "".join(chr(ord("9") - ord(c)) if c.isdigit() else c for c in date)
        return (tier, date_inv)
    postable.sort(key=_sort_key)
    tier_summary = ", ".join(
        f"{_TIER_LABELS.get(t, f'Tier {t}')}: {len(js)}"
        for t, js in sorted(by_tier.items())
    )
    print(f"[*] Scrape complete. {len(jobs)} eligible ({source_summary}). "
          f"{tier_summary}. "
          f"{len(postable)} new to post ({len(seen)} keys in seen list).")

    processed = postable[:config.get("max_results_per_run", 30)]
    if len(postable) > len(processed):
        print(f"[*] Capped at {len(processed)} this run; the other {len(postable) - len(processed)} go out next run.")

    if dry_run:
        for j in processed:
            badge = j.get("badge", "")
            tier_label = _TIER_LABELS.get(j.get("tier"), "?")
            print(f"    [dry-run] [{tier_label}] {j.get('title')} | {j.get('company')} "
                  f"| {j.get('location')} {badge}")
        print("[✔] Dry run: nothing posted, seen list not updated.")
        return

    webhook = config["discord_webhook_url"]
    if not webhook:
        print("[!] DISCORD_WEBHOOK_URL not set; nothing posted and seen list not updated.")
    else:
        for j in processed:
            if send_to_discord(j, webhook):
                seen.mark(j)
                seen.save()
        seen.save()

    if config["sheet_enabled"]:
        send_to_google_sheet(processed, config["google_sheet_webhook"])
    else:
        print("[*] Google Sheet sink disabled (set SHEET_ENABLED=true to enable).")

    print("[✔] Pipeline execution completed.")

if __name__ == "__main__":
    # Windows consoles default to cp1252, which can't print the emoji in log lines.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Run once and exit (the only mode; kept for CI/CD compatibility)")
    parser.add_argument("--dry-run", action="store_true", help="Scrape and print new jobs without posting or updating data/seen.json")
    args = parser.parse_args()

    run_pipeline(dry_run=args.dry_run)