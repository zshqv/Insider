"""Send one fake lead to the Google Sheet web app and print exactly what happened.

Usage (from the repo root):  python scripts/test_sheet.py
Reads GOOGLE_SHEET_WEBHOOK from .env or the environment. Never prints the URL itself.
"""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from dotenv import load_dotenv  # noqa: E402

from insider.sinks.sheet import SheetClient, SheetError  # noqa: E402
from insider.util import env  # noqa: E402


def main():
    load_dotenv()
    url = env("GOOGLE_SHEET_WEBHOOK")
    if not url:
        print("FAIL: GOOGLE_SHEET_WEBHOOK is not set. Copy .env.example to .env and fill it in.")
        return 1
    if not url.startswith("https://script.google.com/macros/s/") or not url.rstrip("/").endswith("/exec"):
        print("WARN: GOOGLE_SHEET_WEBHOOK doesn't look like a web app URL "
              "(expected https://script.google.com/macros/s/.../exec). Continuing anyway.")

    client = SheetClient(url)

    print("1) Health check (GET) ...")
    try:
        info = client.health()
    except SheetError as e:
        print(f"   FAIL: {e}")
        return 1
    print(f"   OK  script version {info['version']} | spreadsheet '{info['spreadsheet']}' "
          f"| tab '{info['sheet']}' | {info['data_rows']} data rows")
    print(f"   headers: {info['headers']}")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    lead = {
        "date_posted": datetime.now().strftime("%Y-%m-%d"),
        "title": "TEST LEAD - delete me",
        "company": "Insider Test Co",
        "location": "Mumbai, India",
        "source": "test_sheet.py",
        "url": f"https://example.com/insider-test/{stamp}",
        "workplace": "Hybrid",
        "tier": "Tier 1 - High Priority",
    }

    print("2) Append one fake lead (POST) ...")
    try:
        result = client.append([lead])[0]
    except SheetError as e:
        print(f"   FAIL: {e}")
        return 1
    if result.get("status") != "ok":
        print(f"   FAIL: {result}")
        return 1
    print(f"   OK  written to row {result['row']} of tab '{info['sheet']}'")

    print("3) Send the same lead again; it should be rejected as a duplicate ...")
    try:
        again = client.append([lead])[0]
    except SheetError as e:
        print(f"   FAIL: {e}")
        return 1
    if again.get("status") != "duplicate":
        print(f"   FAIL: expected 'duplicate', got {again}")
        return 1
    print("   OK  duplicate detected, nothing written")

    print(f"\nPASS. Check row {result['row']} in the sheet, then delete the test row.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
