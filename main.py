import sys
import time
from datetime import datetime
from scraper import JobScraper, load_config
from crm import CRMNotifier


def run_pipeline():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🚀 Launching Insider Sourcing Pipeline...")
    
    config = load_config()
    scraper = JobScraper(config)
    leads = scraper.run()
    
    if leads:
        crm = CRMNotifier()
        crm.push_to_discord(leads)
        crm.push_to_google_sheet(leads)
    else:
        print("ℹ️ Pipeline finished: No new leads found matching your criteria.")


def main():
    if "--once" in sys.argv:
        run_pipeline()
        return

    config = load_config()
    interval_hours = float(config.get("check_interval_hours", 0.5))
    interval_seconds = int(interval_hours * 3600)
    interval_minutes = int(interval_hours * 60)
    
    print("=" * 60)
    print("        INSIDER: Inbound Career Intelligence Engine        ")
    print(f"        Interval: Every {interval_minutes} Minute(s)                     ")
    print("=" * 60)
    
    try:
        while True:
            run_pipeline()
            print(f"\n⏳ Pipeline sleeping for {interval_minutes} minute(s). Press Ctrl+C to terminate.")
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("\n\n🛑 Insider engine terminated cleanly by user.")


if __name__ == "__main__":
    main()