import os
import requests


class CRMNotifier:
    def __init__(self):
        self.discord_webhook = os.getenv("DISCORD_WEBHOOK_URL")
        self.sheet_webhook = os.getenv("GOOGLE_SHEET_WEBHOOK")

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
        if not self.sheet_webhook:
            print("ℹ️ Google Sheet Webhook URL not configured. Skipping Sheet append.")
            return

        formatted_rows = []
        for lead in leads:
            url = lead.get("url", "")
            link_formula = f'=HYPERLINK("{url}", "Apply →")' if url else "N/A"
            
            row = [
                lead.get("date", "N/A"),             # Col A: Date Added
                lead.get("title", "N/A"),            # Col B: Job Title
                lead.get("company", "N/A"),          # Col C: Company
                lead.get("location", "N/A"),         # Col D: Location
                "Arbeitnow API",                      # Col E: Source/Platform
                link_formula,                        # Col F: Application Link
                "New Lead",                          # Col G: Application Status
                "85 - Automated ingestion via Cloud" # Col H: Match Score / Notes
            ]
            formatted_rows.append(row)

        try:
            response = requests.post(self.sheet_webhook, json={"rows": formatted_rows}, timeout=15)
            response.raise_for_status()
            print(f"🚀 Successfully appended {len(formatted_rows)} row(s) to Google Sheets!")
        except Exception as e:
            print(f"⚠️ Failed to push leads to Google Sheets: {e}")