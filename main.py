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

    config["discord_webhook_url"] = discord_url
    config["google_sheet_webhook"] = sheet_url
    return config

def send_to_discord(job, webhook_url):
    if not webhook_url or "YOUR_DISCORD_WEBHOOK" in webhook_url:
        print("[!] Discord webhook URL not configured.")
        return

    is_prio = job.get("is_priority", False)
    
    # Styling
    color = 0xF59E0B if is_prio else 0x3B82F6
    tag = "⚡ **HIGH PRIORITY LEAD**" if is_prio else "🌐 **GLOBAL / SECONDARY LEAD**"
    
    embed = {
        "title": f"💼 {job['title']}",
        "description": f"{tag}\n\n**Company:** `{job.get('company', 'N/A')}`\n**Location:** `{job.get('location', 'N/A')}`",
        "color": color,
        "fields": [
            {"name": "📍 Workplace", "value": f"`{job.get('workplace_type', 'N/A')}`", "inline": True},
            {"name": "📡 Source", "value": f"`{job.get('source', 'N/A')}`", "inline": True},
            {"name": "🔗 Application", "value": f"[**Apply directly on {job.get('source', 'Portal')} ↗**]({job.get('url')})", "inline": False}
        ],
        "footer": {
            "text": f"Career Intelligence Pipeline  •  {job.get('date')}"
        }
    }

    try:
        res = requests.post(webhook_url, json={"embeds": [embed]}, timeout=10)
        res.raise_for_status()
        print(f"[✔] Upgraded Discord alert sent for: {job.get('title')}")
    except Exception as e:
        print(f"[!] Failed to send job to Discord: {e}")

def send_to_google_sheet(job, webhook_url):
    print(f"[*] Attempting Sheet sync for: {job.get('title')}")
    
    if not webhook_url or "YOUR_GOOGLE_SHEET" in webhook_url:
        print("[!] ERROR: GOOGLE_SHEET_WEBHOOK environment variable is missing or unconfigured in GitHub Secrets!")
        return

    masked_url = webhook_url[:40] + "..." if len(webhook_url) > 40 else webhook_url
    print(f"[*] Targeting Webhook URL: {masked_url}")

    payload = {
        "title": job.get("title"),
        "company": job.get("company"),
        "location": job.get("location"),
        "source": job.get("source"),
        "url": job.get("url"),
        "workplace": job.get("workplace_type")
    }

    try:
        res = requests.post(
            webhook_url, 
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            allow_redirects=True,
            timeout=15
        )
        print(f"[*] Sheet API Status Code: {res.status_code}")
        print(f"[*] Sheet API Raw Response: {res.text}")
        
        if res.status_code == 200:
            print(f"[✔] Pushed to Sheet: {job.get('title')}")
        else:
            print(f"[!] Sheet POST returned non-200 status code: {res.status_code}")

    except Exception as e:
        print(f"[!] Exception during Google Sheet HTTP POST: {e}")

def run_pipeline(once=False):
    config = load_config()
    engine = JobScraperEngine(config_path="config.json")
    
    print("[*] Starting Job Ingestion Pipeline Execution...")
    jobs = engine.run_all()
    print(f"[*] Scrape complete. Found {len(jobs)} eligible roles.")

    for job in jobs[:config.get("max_results_per_run", 30)]:
        send_to_discord(job, config["discord_webhook_url"])
        send_to_google_sheet(job, config["google_sheet_webhook"])

    print("[✔] Pipeline execution completed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Run once and exit (for CI/CD)")
    args = parser.parse_args()

    run_pipeline(once=args.once)