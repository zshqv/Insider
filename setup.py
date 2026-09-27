import json
import os
import sys

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "target_roles": ["Software Engineer", "Backend Developer", "Data Analyst"],
    "target_locations": ["Remote", "United States", "India", "Germany"],
    "experience_level": ["Entry-level", "Junior", "Mid-level"],
    "discord_webhook_url": "",
    "google_sheet_id": "",
    "check_interval_hours": 0.5,  # 30 Minutes
    "max_results_per_run": 25,
}


def print_header():
    print("=" * 60)
    print("        INSIDER: Career Intelligence Engine Setup        ")
    print("=" * 60)
    print("Configure your job sourcing parameters, filters, and CRM sync.\n")


def prompt_list(prompt_text, default_list):
    print(f"\n{prompt_text}")
    print(f"Current defaults: {', '.join(default_list)}")
    user_input = input("Enter values (comma-separated, or press Enter to keep default): ").strip()
    
    if not user_input:
        return default_list
    return [item.strip() for item in user_input.split(",") if item.strip()]


def prompt_string(prompt_text, default_value="", required=False):
    while True:
        default_display = f" [{default_value}]" if default_value else ""
        user_input = input(f"\n{prompt_text}{default_display}: ").strip()
        
        if user_input:
            return user_input
        if default_value:
            return default_value
        if not required:
            return ""
        
        print("❌ This field is required. Please enter a valid value.")


def run_setup():
    print_header()
    
    config = {}
    
    # Target Roles
    config["target_roles"] = prompt_list(
        "1. Specify Target Job Titles / Roles:",
        DEFAULT_CONFIG["target_roles"]
    )
    
    # Target Locations
    config["target_locations"] = prompt_list(
        "2. Specify Target Locations / Regions:",
        DEFAULT_CONFIG["target_locations"]
    )
    
    # Experience Levels
    config["experience_level"] = prompt_list(
        "3. Specify Experience Levels:",
        DEFAULT_CONFIG["experience_level"]
    )
    
    # Discord Integration
    print("\n" + "-" * 40)
    print("DISCORD NOTIFICATIONS")
    print("-" * 40)
    config["discord_webhook_url"] = prompt_string(
        "Enter your Discord Webhook URL (optional, press Enter to skip)",
        required=False
    )
    
    # Google Sheets CRM Integration
    print("\n" + "-" * 40)
    print("GOOGLE SHEETS CRM INTEGRATION")
    print("-" * 40)
    config["google_sheet_id"] = prompt_string(
        "Enter your Google Sheet ID (from the spreadsheet URL)",
        required=False
    )
    
    # Execution Settings
    print("\n" + "-" * 40)
    print("PIPELINE EXECUTION SETTINGS")
    print("-" * 40)
    
    interval_input = prompt_string(
        "Scrape check interval in hours (e.g., 0.5 for 30 mins)",
        default_value=str(DEFAULT_CONFIG["check_interval_hours"])
    )
    try:
        config["check_interval_hours"] = float(interval_input)
    except ValueError:
        config["check_interval_hours"] = 0.5

    max_input = prompt_string(
        "Maximum leads to extract per run",
        default_value=str(DEFAULT_CONFIG["max_results_per_run"])
    )
    config["max_results_per_run"] = int(max_input) if max_input.isdigit() else 25

    # Save to config.json
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

    print("\n" + "=" * 60)
    print(f"✅ Configuration successfully saved to '{CONFIG_FILE}'!")
    print("=" * 60)


if __name__ == "__main__":
    run_setup()