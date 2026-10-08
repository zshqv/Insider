"""One-time, idempotent, non-destructive sheet migration.

Usage:
    python scripts/migrate_sheet.py --dry-run       # preview changes
    python scripts/migrate_sheet.py --i-backed-up   # apply changes

What it does:
  1. Calls ensureSchema() via the Apps Script web app (GET request).
  2. Sets blank Status cells to "New" (via the default in Code.gs).
  3. Does NOT convert existing Rejected rows to Skipped.

You must manually back up the sheet first (File -> Download -> CSV).
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from insider.util import env, redact
from insider.sinks.sheet import SheetClient, SheetError


def migrate(dry_run=False):
    load_dotenv()
    webhook = env("GOOGLE_SHEET_WEBHOOK")
    if not webhook:
        print("[!] GOOGLE_SHEET_WEBHOOK not set. Set it in .env or environment.")
        sys.exit(1)

    client = SheetClient(webhook)

    if dry_run:
        print("[*] Dry run — no changes will be made.\n")
        print("[*] Would call GET to trigger ensureSchema() — adds missing columns:")
        print("    Fit, Gate Pass, German Req, Enrollment Req, Visa, Gate Fail Reasons,")
        print("    Gate Confidence, Date Found, Date Applied, Follow-up Date, Skip Reason,")
        print("    Contact, Messaged On, Replied?, Notes, Duplicate Flag")
        print("[*] New leads will default to Status = 'New'.")
        print("[*] Existing 'Rejected' rows will NOT be changed.")
        print("\n[*] After migration, redeploy Code.gs:")
        print("    1. Open Apps Script editor")
        print("    2. Paste the latest apps_script/Code.gs")
        print("    3. Deploy > Manage deployments > Edit > Version: New version > Deploy")
        print("\n[✔] Dry run complete.")
        return

    print("[*] Step 1: Calling GET to trigger ensureSchema()...")
    try:
        result = client.health()
    except SheetError as e:
        print(f"[!] Failed: {e}")
        print("\n[!] If you see a version mismatch, paste the latest Code.gs first:")
        print("    1. Open Apps Script editor")
        print("    2. Replace Code.gs with apps_script/Code.gs from this repo")
        print("    3. Deploy > Manage deployments > Edit > Version: New version > Deploy")
        print("    4. Re-run this script")
        sys.exit(1)

    print(f"[✔] Schema ensured. Script version: {result.get('version')}")
    print(f"    Headers: {result.get('headers')}")
    print(f"    Data rows: {result.get('data_rows')}")
    print("\n[*] New leads will default to Status = 'New'.")
    print("[*] Existing 'Rejected' rows were NOT changed.")
    print("\n[*] Remember to redeploy Code.gs if you haven't already:")
    print("    Deploy > Manage deployments > Edit > Version: New version > Deploy")
    print("\n[✔] Migration complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate Insider sheet to new schema")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying")
    parser.add_argument("--i-backed-up", action="store_true",
                        help="Confirm you backed up the sheet (File > Download > CSV). Required for non-dry-run.")
    args = parser.parse_args()

    if not args.dry_run and not args.i_backed_up:
        print("[!] Before migrating, back up your sheet:")
        print("    1. Open the Google Sheet")
        print("    2. File > Download > Comma Separated Values (.csv)")
        print("    3. Save the file somewhere safe")
        print("\n    Then re-run with: python scripts/migrate_sheet.py --i-backed-up")
        sys.exit(1)

    migrate(dry_run=args.dry_run)
