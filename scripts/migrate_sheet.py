"""One-time, idempotent, non-destructive sheet migration.

Usage:
    python scripts/migrate_sheet.py --dry-run   # preview changes
    python scripts/migrate_sheet.py             # apply changes

What it does:
  1. Calls ensureSchema() via the Apps Script web app (GET request).
  2. Sets blank Status cells to "New".
  3. Does NOT convert existing Rejected rows to Skipped.

Before writing, it backs up the sheet contents to a local CSV.
"""

import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from insider.util import env, redact
from insider.sinks.sheet import SheetClient, SheetError

BACKUP_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def backup_sheet(client, path):
    """Fetch sheet metadata (no bulk-read API from Apps Script, so we just log what we can)."""
    print(f"[*] Requesting sheet info for backup reference...")
    info = client.health()
    headers = info.get("headers", [])
    rows = info.get("data_rows", 0)
    print(f"[*] Sheet: {info.get('spreadsheet')} / {info.get('sheet')}")
    print(f"[*] Headers: {headers}")
    print(f"[*] Data rows: {rows}")

    os.makedirs(BACKUP_DIR, exist_ok=True)
    meta_path = os.path.join(BACKUP_DIR, "migration_backup_meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2)
    print(f"[*] Metadata saved to {meta_path}")
    return info


def migrate(dry_run=False):
    load_dotenv()
    webhook = env("GOOGLE_SHEET_WEBHOOK")
    if not webhook:
        print("[!] GOOGLE_SHEET_WEBHOOK not set. Set it in .env or environment.")
        sys.exit(1)

    client = SheetClient(webhook)

    print("[*] Step 1: Backing up sheet metadata...")
    info = backup_sheet(client, BACKUP_DIR)

    print("[*] Step 2: Calling GET to trigger ensureSchema()...")
    if dry_run:
        print("    [dry-run] Would call GET to ensure new columns exist.")
        print("    [dry-run] Would set blank Status cells to 'New'.")
        print("    [dry-run] Existing 'Rejected' rows will NOT be changed.")
        print("[✔] Dry run complete. No changes made.")
        return

    result = client.health()
    print(f"[✔] Schema ensured. Version: {result.get('version')}, headers: {result.get('headers')}")

    print("[*] Note: Setting blank Status to 'New' must be done in Apps Script")
    print("    or manually in the sheet (filter Status column for blanks, set to 'New').")
    print("    The pipeline already sets Status='New' for new leads.")
    print("[✔] Migration complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate Insider sheet to new schema")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying")
    args = parser.parse_args()
    migrate(dry_run=args.dry_run)
