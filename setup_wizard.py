#!/usr/bin/env python3
"""
GVPL Hold Notifier - Interactive Configuration Wizard
------------------------------------------------------
Guides the user through setting up patrons/cards, notification preferences
(Desktop, WhatsApp, SMS), and Twilio API credentials.
"""

import os
import sys
import json
import re
from pathlib import Path

DEFAULT_CONFIG_DIR = Path.home() / ".config" / "library"
DEFAULT_CREDENTIALS_FILE = DEFAULT_CONFIG_DIR / "credentials.json"

# ANSI Color Codes
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"

def print_header(title):
    print(f"\n{BOLD}{CYAN}=== {title} ==={RESET}")

def prompt_non_empty(prompt_text, default=None):
    while True:
        suffix = f" [{default}]" if default is not None else ""
        val = input(f"{prompt_text}{suffix}: ").strip()
        if not val and default is not None:
            return default
        if val:
            return val
        print(f"{YELLOW}Input cannot be empty. Please try again.{RESET}")

def prompt_int(prompt_text, min_val=1, default=1):
    while True:
        suffix = f" [{default}]" if default is not None else ""
        val = input(f"{prompt_text}{suffix}: ").strip()
        if not val and default is not None:
            return default
        try:
            num = int(val)
            if num >= min_val:
                return num
            print(f"{YELLOW}Please enter a number >= {min_val}.{RESET}")
        except ValueError:
            print(f"{YELLOW}Invalid integer. Please try again.{RESET}")

def run_wizard(config_path=DEFAULT_CREDENTIALS_FILE):
    print_header("GVPL Hold Notifier Setup Wizard")
    print("Welcome! This setup will configure your library cards and notification preferences.\n")

    # 1. Collect Patron Cards
    print_header("1. Patron & Library Card Configuration")
    num_people = prompt_int("How many people/library cards will it track holds for?", min_val=1, default=1)
    
    cards = []
    for i in range(num_people):
        print(f"\n{BOLD}--- Card {i+1} of {num_people} ---{RESET}")
        name = prompt_non_empty(f"Patron name (e.g. Seth)", default=f"Patron {i+1}")
        barcode = prompt_non_empty("Library card barcode number")
        pin = prompt_non_empty("Library card PIN")
        cards.append({
            "name": name,
            "barcode": barcode,
            "pin": pin
        })

    # 2. Notification Methods
    print_header("2. Notification Channels")
    print("How would you like to receive hold notifications?")
    print("  1) Linux Desktop Notifications (notify-send)")
    print("  2) WhatsApp (via Twilio)")
    print("  3) SMS (via Twilio)")
    
    channels = []
    while True:
        choices_input = input("\nEnter choice(s) separated by commas (e.g., 1,2 or 1) [default: 1]: ").strip()
        if not choices_input:
            choices_input = "1"
        
        raw_choices = [c.strip() for c in choices_input.split(",") if c.strip()]
        valid = True
        selected_channels = []
        for choice in raw_choices:
            if choice == "1" and "desktop" not in selected_channels:
                selected_channels.append("desktop")
            elif choice == "2" and "whatsapp" not in selected_channels:
                selected_channels.append("whatsapp")
            elif choice == "3" and "sms" not in selected_channels:
                selected_channels.append("sms")
            else:
                valid = False
                break
        
        if valid and selected_channels:
            channels = selected_channels
            break
        print(f"{YELLOW}Invalid choice(s). Enter numbers 1, 2, or 3 separated by commas.{RESET}")

    # 3. Twilio Configuration (if WhatsApp or SMS selected)
    twilio_account_sid = ""
    twilio_auth_token = ""
    twilio_from_number = ""
    twilio_whatsapp_from = ""
    twilio_to_numbers = []

    needs_twilio = ("whatsapp" in channels) or ("sms" in channels)
    if needs_twilio:
        print_header("3. Twilio Notification Setup")
        
        # Phone numbers to send to
        num_recipients = prompt_int("How many phone numbers should receive notifications?", min_val=1, default=1)
        for j in range(num_recipients):
            phone = prompt_non_empty(f"Recipient phone number {j+1} (E.164 format, e.g., +12505550123)")
            if not phone.startswith("+"):
                phone = f"+{phone}"
            twilio_to_numbers.append(phone)

        # Twilio API credentials
        twilio_account_sid = prompt_non_empty("Twilio Account SID (starts with AC)")
        twilio_auth_token = prompt_non_empty("Twilio Auth Token")

        if "sms" in channels:
            twilio_from_number = prompt_non_empty("Twilio Sender SMS Phone Number (e.g., +18005550199)")

        if "whatsapp" in channels:
            twilio_whatsapp_from = prompt_non_empty("Twilio WhatsApp From Number", default="whatsapp:+14155238886")
            if not twilio_whatsapp_from.startswith("whatsapp:"):
                twilio_whatsapp_from = f"whatsapp:{twilio_whatsapp_from}"

    # 4. Summary & Save
    print_header("4. Configuration Summary")
    print(f"{BOLD}Patron Cards:{RESET} {len(cards)}")
    for c in cards:
        print(f"  • {c['name']} (Barcode: {c['barcode'][:-4]}****)")

    print(f"{BOLD}Enabled Notification Channels:{RESET} {', '.join([c.upper() for c in channels])}")
    
    if needs_twilio:
        print(f"{BOLD}Twilio Recipients:{RESET} {', '.join(twilio_to_numbers)}")
        print(f"{BOLD}Twilio Account SID:{RESET} {twilio_account_sid[:6]}...")
        if twilio_from_number:
            print(f"{BOLD}Twilio SMS From Number:{RESET} {twilio_from_number}")
        if twilio_whatsapp_from:
            print(f"{BOLD}Twilio WhatsApp From Number:{RESET} {twilio_whatsapp_from}")

    config_data = {
        "cards": cards,
        "channels": channels
    }

    if needs_twilio:
        config_data["twilio_account_sid"] = twilio_account_sid
        config_data["twilio_auth_token"] = twilio_auth_token
        config_data["twilio_to_numbers"] = twilio_to_numbers
        if twilio_from_number:
            config_data["twilio_from_number"] = twilio_from_number
        if twilio_whatsapp_from:
            config_data["twilio_whatsapp_from"] = twilio_whatsapp_from

    print("")
    save_confirm = input(f"Save configuration to {config_path}? [Y/n]: ").strip().lower()
    if save_confirm in ("", "y", "yes"):
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            json.dump(config_data, f, indent=2)
        print(f"{GREEN}✓ Configuration saved successfully to {config_path}{RESET}")
        return True
    else:
        print(f"{YELLOW}Configuration not saved.{RESET}")
        return False

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GVPL Hold Notifier Configuration Wizard")
    parser.add_argument("--config", type=Path, default=DEFAULT_CREDENTIALS_FILE, help="Path to credentials JSON file")
    args = parser.parse_args()
    
    try:
        run_wizard(args.config)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Setup wizard cancelled.{RESET}")
        sys.exit(1)
