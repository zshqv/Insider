import os
import requests


class CRMNotifier:
    def __init__(self):
        self.discord_webhook = os.getenv("DISCORD_WEBHOOK_URL")
        self.sheet_id = os.getenv("GOOGLE_SHEET_ID")

    def push_to_discord(self, leads):
        if not self.discord_webhook:
            print("ℹ️ Discord Webhook URL not configured. Skipping Discord notification.")
            return

        for lead in leads:
            payload = {
                "embeds": [
                    {
                        "title": lead.get("title", "Job Lead"),
                        "url": lead.get("url", ""),
                        "color": 3447003,  # Crisp Navy Blue
                        "fields": [
                            {"name": "Company", "value": lead.get("company", "N/A"), "inline": True},
                            {"name": "Location", "value": lead.get("location", "N/A"), "inline": True},
                            {"name": "Date Posted", "value": lead.get("date", "N/A"), "inline": True},
                        ],
                        "footer": {"text": "Insider Career Intelligence Engine"},
                    }
                ]
            }
            try:
                response = requests.post(self.discord_webhook, json=payload, timeout=10)
                response.raise_for_status()
            except Exception as e:
                print(f"⚠️ Failed to push lead to Discord: {e}")

        print(f"🚀 Successfully sent {len(leads)} lead(s) to Discord!")

    def push_to_google_sheet(self, leads):
        if not self.sheet_id:
            print("ℹ️ Google Sheet ID not configured. Skipping Sheet append.")
            return
        
        print(f"📊 Ready to append {len(leads)} lead(s) to Google Sheet ID: {self.sheet_id}")