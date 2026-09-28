import os
import json
import argparse
import requests
from scraper import JobScraperEngine

def load_config(config_path="config.json"):
    with open(config_path, "r") as f:
        config = json.load(f)
    
    # Priority: Environment Variables (GitHub Secrets) > config.json
    discord_url = os.environ.get("DISCORD_WEBHOOK_URL") or config.get("discord_webhook_url")
    sheet_url = os.environ.get("GOOGLE_SHEET_WEBHOOK") or config.get("google_sheet_webhook")

    config["discord_webhook_url"] = discord_url
    config["google_sheet_webhook"] = sheet_url
    return config

def send_to_discord(job, webhook_url):
    if not webhook_url or "YOUR_DISCORD_WEBHOOK_URL" in webhook_url:
        print("[!] Discord webhook URL not configured.")
        return

    priority_prefix = "⚡ [HIGH PRIORITY] " if job.get("is_priority") else "🌐 "
    embed = {
        "title": f"{priority_prefix}{job['title']}",
        "color": 5814783 if job.get("is_priority") else 3447003,
        "fields": [
            {"name": "Company", "value": job.get("company", "N/A"), "inline": True},
            {"name": "Location", "value": job.get("location", "N/A"), "inline": True},
            {"name": "Workplace", "value": job.get("workplace_type", "N/A"), "inline": True},
            {"name": "Source", "value": job.get("source", "N/A"), "inline": True},
            {"name": "Apply Link", "value": f"[Apply Here]({job.get('url')})", "inline": False}
        ],
        "footer": {"text": f"Ingestion Pipeline | {job.get('date')}"}
    }

    try:
        res = requests.post(webhook_url, json={"embeds": [embed]}, timeout=10)
        res.raise_for_status()
    except Exception as e:
        print(f"[!] Failed to send job to Discord: {e}")

def send_to_google_sheet(job, webhook_url):
    if not webhook_url or "YOUR_GOOGLE_SHEET_WEBHOOK" in webhook_url:
        print("[!] Google Sheet webhook URL not configured.")
        return

    workplace_and_prio = job.get("workplace_type", "On-site 🏢")
    if job.get("is_priority"):
        workplace_and_prio += " | ⚡ HIGH PRIORITY"
    else:
        workplace_and_prio += " | 🌐 GLOBAL TIER"

    payload = {
        "date": job.get("date"),
        "title": job.get("title"),
        "company": job.get("company"),
        "location": job.get("location"),
        "source": job.get("source"),
        "url": job.get("url"),
        "status": "New Lead",
        "notes": workplace_and_prio
    }

    try:
        res = requests.post(
            webhook_url, 
            json=payload, 
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        res.raise_for_status()
        print(f"[✔] Pushed to Sheet: {job.get('title')}")
    except Exception as e:
        print(f"[!] Failed to send job to Google Sheet: {e}")

def run_pipeline(once=False):
    config = load_config()
    engine = JobScraperEngine(config_path="config.json")
    
    print("[*] Running job ingestion pipeline...")
    jobs = engine.run_all()
    print(f"[*] Found {len(jobs)} total matching positions.")

    for job in jobs[:config.get("max_results_per_run", 30)]:
        send_to_discord(job, config["discord_webhook_url"])
        send_to_google_sheet(job, config["google_sheet_webhook"])

    print("[✔] Ingestion cycle complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Run once and exit (for GitHub Actions)")
    args = parser.parse_args()

    run_pipeline(once=args.once)