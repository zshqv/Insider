import json
import os
import requests


def load_config():
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except Exception:
        return {}


class CRMNotifier:
    def __init__(self):
        config = load_config()
        self.discord_webhook = os.getenv("DISCORD_WEBHOOK_URL") or config.get("discord_webhook_url")
        self.sheet_webhook = os.getenv("GOOGLE_SHEET_WEBHOOK") or config.get("google_sheet_webhook")

    def push_to_discord(self, leads):
        if not self.discord_webhook:
            print("ℹ️ Discord Webhook URL not configured. Skipping Discord notification.")
            return

        for lead in leads:
            title = lead.get("title", "Job Lead")
            url = lead.get("url", "")
            company = lead.get("company", "N/A")
            location = lead.get("location", "N/A")
            date_posted = lead.get("date", "N/A")
            source = lead.get("source", "Aggregated Pipeline")

            payload = {
                "embeds": [
                    {
                        "title": f"💼 {title}",
                        "url": url,
                        "color": 15258703,  # Emerald Green (#E8D52F / #00D166)
                        "description": f"⚡ **New High-Intent Finance Role Detected**\nDirect application pipeline match via **{source}**.",
                        "fields": [
                            {"name": "🏢 Company", "value": f"`{company}`", "inline": True},
                            {"name": "📍 Location", "value": f"`{location}`", "inline": True},
                            {"name": "📅 Posted Date", "value": f"`{date_posted}`", "inline": True},
                        ],
                        "footer": {
                            "text": "Insider Career Intelligence Engine • Early-Career Finance",
                            "icon_url": "https://cdn-icons-png.flaticon.com/512/3135/3135715.png"
                        }
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
        if not self.sheet_webhook:
            print("ℹ️ Google Sheet Webhook URL not configured. Skipping Sheet append.")
            return

        formatted_rows = []
        for lead in leads:
            url = lead.get("url", "")
            link_formula = f'=HYPERLINK("{url}", "Apply →")' if url else "N/A"
            
            row = [
                lead.get("date", "N/A"),               # Col A: Date Added
                lead.get("title", "N/A"),              # Col B: Job Title
                lead.get("company", "N/A"),            # Col C: Company
                lead.get("location", "N/A"),           # Col D: Location
                lead.get("source", "API Ingestion"),   # Col E: Source/Platform
                link_formula,                          # Col F: Application Link
                "New Lead",                            # Col G: Application Status
                "Ingested via Cloud Pipeline"          # Col H: Clean Notes
            ]
            formatted_rows.append(row)

        payload = json.dumps({"rows": formatted_rows})

        try:
            response = requests.post(
                self.sheet_webhook, 
                data=payload,
                headers={"Content-Type": "text/plain"},
                timeout=15
            )
            print(f"📊 Webhook Response Status: {response.status_code}")
            print(f"📄 Response Text: {response.text}")
            print(f"🚀 Successfully appended {len(formatted_rows)} row(s) to Google Sheets!")
        except Exception as e:
            print(f"⚠️ Failed to push leads to Google Sheets: {e}")