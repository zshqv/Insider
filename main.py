import os
import json
import argparse
import requests
from scraper import JobScraperEngine

def load_config(config_path="config.json"):
    with open(config_path, "r") as f:
        config = json.load(f)
    
    discord_url = os.environ.get("DISCORD_WEBHOOK_URL") or config.get("discord_webhook_url")
    sheet_url = os.environ.get("GOOGLE_SHEET_WEBHOOK") or config.get("google_sheet_webhook")

    if discord_url:
        discord_url = str(discord_url).strip("[]'\" ")
    if sheet_url:
        sheet_url = str(sheet_url).strip("[]'\" ")

    config["discord_webhook_url"] = discord_url
    config["google_sheet_webhook"] = sheet_url
    return config

def send_to_discord(job, webhook_url):
    if not webhook_url or "YOUR_DISCORD_WEBHOOK" in webhook_url:
        print("[!] Discord webhook URL not configured.")
        return

    is_prio = job.get("is_priority", False)
    color = 0xF59E0B if is_prio else 0x3B82F6
    badge = "⚡ **HIGH PRIORITY LEAD**" if is_prio else "🌐 **GLOBAL / SECONDARY LEAD**"
    date_posted = job.get("date_posted", "Recently")
    
    embed = {
        "title": f"💼 {job['title']}",
        "description": (
            f"{badge}\n\n"
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

    try:
        res = requests.post(webhook_url, json={"embeds": [embed]}, timeout=10)
        res.raise_for_status()
        print(f"[✔] Discord alert sent for: {job.get('title')}")
    except Exception as e:
        print(f"[!] Failed to send job to Discord: {e}")

def send_to_google_sheet(job, webhook_url):
    if not webhook_url or "YOUR_GOOGLE_SHEET" in webhook_url or not webhook_url.startswith("http"):
        return

    payload = {
        "title": job.get("title"),
        "company": job.get("company"),
        "location": job.get("location"),
        "source": job.get("source"),
        "url": job.get("url"),
        "workplace": job.get("workplace_type"),
        "date_posted": job.get("date_posted")
    }

    try:
        requests.post(
            webhook_url, 
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            allow_redirects=True,
            timeout=15
        )
    except Exception as e:
        print(f"[!] Exception during Google Sheet HTTP POST: {e}")

def run_pipeline(once=False):
    config = load_config()
    engine = JobScraperEngine(config_path="config.json")
    
    print("[*] Starting Job Ingestion Pipeline Execution...")
    jobs = engine.run_all()
    print(f"[*] Scrape complete. Found {len(jobs)} eligible roles.")

    processed = jobs[:config.get("max_results_per_run", 30)]

    for job in processed:
        send_to_discord(job, config["discord_webhook_url"])
        send_to_google_sheet(job, config["google_sheet_webhook"])

    print("[✔] Pipeline execution completed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Run once and exit (for CI/CD)")
    args = parser.parse_args()

    run_pipeline(once=args.once)