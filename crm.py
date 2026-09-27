import json
import os
import sys
import requests
import gspread
from google.oauth2.service_account import Credentials


class CRMNotifier:
    def __init__(self, config_path="config.json"):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)
            
        self.discord_url = self.config.get("discord_webhook_url", "")
        self.sheet_id = self.config.get("google_sheet_id", "")

    def push_to_discord(self, leads):
        if not self.discord_url:
            print("ℹ️ Discord Webhook URL not configured. Skipping Discord notification.")
            return

        print(f"🔔 Dispatching {len(leads)} leads to Discord...")
        for lead in leads:
            embed = {
                "title": f"🎯 New Role: {lead['title']}",
                "url": lead["url"],
                "color": 3447003,  # Blue accent
                "fields": [
                    {"name": "Company", "value": lead["company"], "inline": True},
                    {"name": "Location", "value": lead["location"], "inline": True},
                    {"name": "Remote", "value": str(lead["remote"]), "inline": True},
                    {"name": "Tags", "value": lead["tags"] if lead["tags"] else "N/A", "inline": False}
                ],
                "footer": {"text": f"Insider Engine • {lead['scraped_at']}"}
            }
            
            payload = {"embeds": [embed]}
            try:
                res = requests.post(self.discord_url, json=payload, timeout=5)
                res.raise_for_status()
            except requests.RequestException as e:
                print(f"❌ Failed to send Discord alert for {lead['title']}: {e}")

    def push_to_google_sheet(self, leads):
        if not self.sheet_id:
            print("ℹ️ Google Sheet ID not configured. Skipping Sheet append.")
            return

        creds_path = "credentials.json"
        if not os.path.exists(creds_path):
            print(f"⚠️ Service account file '{creds_path}' missing. Place your Google API key JSON in the root directory to enable Sheets CRM.")
            return

        print("📊 Appending leads to Google Sheets CRM...")
        try:
            scopes = ["https://www.googleapis.com/auth/spreadsheets"]
            creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
            client = gspread.authorize(creds)
            
            sheet = client.open_by_key(self.sheet_id).sheet1
            
            # Write Header if sheet is empty
            if len(sheet.get_all_values()) == 0:
                sheet.append_row(["Title", "Company", "Location", "Remote", "URL", "Tags", "Date Scraped"])

            rows = [
                [l["title"], l["company"], l["location"], str(l["remote"]), l["url"], l["tags"], l["scraped_at"]]
                for l in leads
            ]
            sheet.append_rows(rows)
            print(f"✅ Appended {len(rows)} rows to Google Sheet.")
        except Exception as e:
            print(f"❌ Google Sheets Sync Error: {e}")


if __name__ == "__main__":
    from scraper import JobScraper, load_config
    
    cfg = load_config()
    scraper = JobScraper(cfg)
    leads = scraper.run()
    
    if leads:
        crm = CRMNotifier()
        crm.push_to_discord(leads)
        crm.push_to_google_sheet(leads)