#!/usr/bin/env python3
"""
GVPL (Greater Victoria Public Library) Hold Notifier
---------------------------------------------------
Automated library hold checker for SirsiDynix Enterprise (gvpl.ca).
Bypasses Cloudflare WAF / JS verification using headless browser automation,
parses patron hold statuses from config file credentials, and dispatches
notifications via Desktop (notify-send) and Twilio WhatsApp.
"""

import os
import sys
import json
import re
import html
import time
import argparse
import subprocess
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options

DEFAULT_CONFIG_DIR = Path.home() / ".config" / "library"
DEFAULT_CREDENTIALS_FILE = DEFAULT_CONFIG_DIR / "credentials.json"
DEFAULT_STATE_FILE = DEFAULT_CONFIG_DIR / "holds_state.json"

def load_credentials(config_path):
    if not config_path.exists():
        print(f"Error: Credentials file not found at {config_path}")
        print("Copy credentials.example.json to ~/.config/library/credentials.json and fill in your library barcode & PIN.")
        sys.exit(1)
    with open(config_path, "r") as f:
        return json.load(f)

def get_cards(creds):
    cards = creds.get("cards", [])
    valid_cards = []
    if isinstance(cards, list) and len(cards) > 0:
        for idx, c in enumerate(cards):
            if isinstance(c, dict):
                barcode = str(c.get("barcode", "")).strip()
                pin = str(c.get("pin", "")).strip()
                name = str(c.get("name", "")).strip()
                if barcode and pin:
                    valid_cards.append({
                        "name": name if name else f"Card {idx + 1}",
                        "barcode": barcode,
                        "pin": pin
                    })
        return valid_cards

    # Single card format support from config
    barcode = str(creds.get("barcode", "")).strip()
    pin = str(creds.get("pin", "")).strip()
    name = str(creds.get("name", "")).strip()
    if barcode and pin:
        return [{"name": name if name else "Account", "barcode": barcode, "pin": pin}]
        
    return []

def load_previous_state(state_path):
    if state_path.exists():
        try:
            with open(state_path, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_current_state(state_path, state):
    state_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Saving state to {state_path}")
    with open(state_path, "w") as f:
        json.dump(state, f, indent=2)

def notify_desktop(title, message):
    try:
        subprocess.run(["notify-send", "-i", "bookmark", title, message], check=False)
        print("Desktop notification dispatched.")
    except Exception as e:
        print(f"Desktop notification failed: {e}")

def notify_twilio_whatsapp(sid, auth_token, from_num, to_num, message):
    if not (sid and auth_token and from_num and to_num):
        return
    try:
        import urllib.parse
        import urllib.request
        import base64

        url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
        if not from_num.startswith("whatsapp:"):
            from_num = f"whatsapp:{from_num}"
        if not to_num.startswith("whatsapp:"):
            to_num = f"whatsapp:{to_num}"

        data = urllib.parse.urlencode({
            "From": from_num,
            "To": to_num,
            "Body": message
        }).encode('utf-8')

        req = urllib.request.Request(url, data=data)
        auth_header = base64.b64encode(f"{sid}:{auth_token}".encode('utf-8')).decode('utf-8')
        req.add_header("Authorization", f"Basic {auth_header}")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")

        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status in (200, 201):
                print(f"Twilio WhatsApp notification sent successfully to {to_num}.")
    except Exception as e:
        print(f"Twilio WhatsApp notification to {to_num} failed: {e}")

def notify_twilio_sms(sid, auth_token, from_num, to_num, message):
    if not (sid and auth_token and from_num and to_num):
        return
    try:
        import urllib.parse
        import urllib.request
        import base64

        url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
        clean_from = from_num.replace("whatsapp:", "").strip()
        clean_to = to_num.replace("whatsapp:", "").strip()

        data = urllib.parse.urlencode({
            "From": clean_from,
            "To": clean_to,
            "Body": message
        }).encode('utf-8')

        req = urllib.request.Request(url, data=data)
        auth_header = base64.b64encode(f"{sid}:{auth_token}".encode('utf-8')).decode('utf-8')
        req.add_header("Authorization", f"Basic {auth_header}")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")

        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status in (200, 201):
                print(f"Twilio SMS notification sent successfully to {clean_to}.")
    except Exception as e:
        print(f"Twilio SMS notification to {clean_to} failed: {e}")

def get_to_numbers(creds):
    to_val = creds.get("twilio_to_number", creds.get("twilio_to_numbers", []))
    if isinstance(to_val, list):
        return [str(n).strip() for n in to_val if str(n).strip()]
    elif isinstance(to_val, str) and to_val.strip():
        return [n.strip() for n in to_val.split(",") if n.strip()]
    return []

def send_whatsapp_notifications(creds, message):
    sid = str(creds.get("twilio_account_sid", "")).strip()
    auth_token = str(creds.get("twilio_auth_token", "")).strip()
    from_num = str(creds.get("twilio_whatsapp_from", creds.get("twilio_from_number", ""))).strip()
    to_numbers = get_to_numbers(creds)

    if sid and auth_token and from_num and to_numbers:
        for to_num in to_numbers:
            notify_twilio_whatsapp(sid, auth_token, from_num, to_num, message)

def send_sms_notifications(creds, message):
    sid = str(creds.get("twilio_account_sid", "")).strip()
    auth_token = str(creds.get("twilio_auth_token", "")).strip()
    from_num = str(creds.get("twilio_from_number", "")).strip()
    to_numbers = get_to_numbers(creds)

    if sid and auth_token and from_num and to_numbers:
        for to_num in to_numbers:
            notify_twilio_sms(sid, auth_token, from_num, to_num, message)

def check_gvpl_account(barcode, pin):
    options = Options()
    options.add_argument('--headless')
    
    driver = None
    try:
        driver = webdriver.Firefox(options=options)
        driver.get('https://gvpl.ca/client/en_US/default')
        time.sleep(3) # Cloudflare verification redirect
        
        # 1. Open login modal (retry up to 15s for Cloudflare / DOM render)
        login_trigger = None
        for _ in range(15):
            try:
                login_trigger = driver.find_element(By.XPATH, "//a[contains(@class, 'loginLink') or contains(text(), 'Log In')]")
                if login_trigger:
                    driver.execute_script('arguments[0].click();', login_trigger)
                    break
            except Exception:
                time.sleep(1)
        if not login_trigger:
            raise Exception("Login link element not found on landing page.")
        time.sleep(1)
        
        # 2. Fill credentials & submit
        user_input = driver.find_element(By.ID, 'j_username')
        driver.execute_script('arguments[0].value = arguments[1];', user_input, barcode)
        
        pass_input = driver.find_element(By.ID, 'j_password')
        driver.execute_script('arguments[0].value = arguments[1];', pass_input, pin)
        
        submit_btn = driver.find_element(By.ID, 'submit_0')
        driver.execute_script('arguments[0].click();', submit_btn)
        
        # 3. Wait for post-login redirect to My Account page
        for _ in range(15):
            time.sleep(1)
            if "Log Out" in driver.page_source or "account" in driver.current_url.lower():
                break
                
        # 4. Click Holds tab & get expected holds count
        holds_tab = None
        expected_count = -1
        for _ in range(15):
            try:
                holds_tab = driver.find_element(By.XPATH, "//a[@href='#holdsTab'] | //a[contains(@aria-controls, 'holdsTab')]")
                if holds_tab:
                    tab_text = holds_tab.text
                    match = re.search(r'Holds\s*\(\s*(\d+)\s*\)', tab_text, re.IGNORECASE)
                    if match:
                        expected_count = int(match.group(1))
                    driver.execute_script('arguments[0].click();', holds_tab)
                    break
            except Exception:
                time.sleep(1)
                
        ready_holds = []
        in_transit_holds = []
        total_holds_count = 0
        
        # 5. Wait for hold table rows to populate in live DOM
        rows = []
        for attempt in range(25):
            time.sleep(1)
            if expected_count > 0 and attempt > 0 and attempt % 5 == 0 and holds_tab:
                try:
                    driver.execute_script('arguments[0].click();', holds_tab)
                except Exception:
                    pass
                    
            table_rows = driver.find_elements(By.XPATH, "//div[@id='holdsTab']//table//tr[td] | //table//tr[td]")
            valid_rows = []
            for r in table_rows:
                cells = r.find_elements(By.TAG_NAME, "td")
                if len(cells) >= 4:
                    title_raw = cells[1].text.strip()
                    # Filter out header rows and personal info summary rows
                    if title_raw and "Title / Format" not in title_raw and not title_raw.isdigit() and len(title_raw) > 5:
                        valid_rows.append(r)
                        
            if len(valid_rows) >= max(1, expected_count):
                rows = valid_rows
                break
            elif len(valid_rows) > 0 and expected_count == 0:
                rows = valid_rows
                break
            elif len(valid_rows) > 0 and attempt >= 20:
                rows = valid_rows

        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) >= 4:
                title_raw = cells[1].text.strip()
                status_raw = cells[2].text.strip()
                pickup_raw = cells[3].text.strip()
                
                if not title_raw or "Title / Format" in title_raw:
                    continue
                    
                total_holds_count += 1
                
                # Take main title line (strip format like Book / eAudiobook)
                title = title_raw.split('\n')[0].strip()
                entry = f"{title} ({pickup_raw})" if pickup_raw else title
                
                s_lower = status_raw.lower()
                if any(kw in s_lower for kw in ['being held', 'held', 'ready', 'pick up']):
                    ready_holds.append(entry)
                elif 'transit' in s_lower:
                    in_transit_holds.append(entry)
                    
        return {
            "total": total_holds_count,
            "ready": ready_holds,
            "in_transit": in_transit_holds
        }
        
    except Exception as e:
        print(f"Error checking GVPL account: {e}")
        return {"total": 0, "ready": [], "in_transit": []}
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

def main():
    parser = argparse.ArgumentParser(description="GVPL Library Hold Notifier")
    parser.add_argument("--config", type=Path, default=DEFAULT_CREDENTIALS_FILE, help="Path to credentials JSON file")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE_FILE, help="Path to state JSON file")
    parser.add_argument("--force-notify", action="store_true", help="Send notification regardless of state changes")
    parser.add_argument("--dry-run", action="store_true", help="Perform check without updating state file")
    args = parser.parse_args()

    creds = load_credentials(args.config)
    cards = get_cards(creds)
    
    active_cards = [c for c in cards if c.get("barcode", "").strip() and c.get("pin", "").strip()]
    
    if not active_cards:
        print(f"Error: No active card credentials found in {args.config}")
        sys.exit(1)
        
    prev_state = load_previous_state(args.state)
    current_state = {}
    
    has_changes = False
    card_results = []
    
    for card in active_cards:
        name = card.get("name", "Account")
        barcode = card["barcode"].strip()
        pin = card["pin"].strip()
        
        print(f"Checking GVPL account for {name}...")
        data = check_gvpl_account(barcode, pin)
        
        card_prev = prev_state.get(name, {})
        prev_total = card_prev.get("total", 0)
        
        # Safeguard: If current fetch returned fewer holds than previously recorded, preserve previous valid state
        if prev_total > 1 and data["total"] < prev_total:
            print(f"Warning: Fetching holds for {name} returned {data['total']} items (expected {prev_total}); preserving previous valid state.")
            data = card_prev

        current_state[name] = data
        
        total = data["total"]
        ready = data["ready"]
        in_transit = data["in_transit"]
        
        prev_ready = set(card_prev.get("ready", []))
        current_ready = set(ready)
        new_ready = current_ready - prev_ready
        
        prev_in_transit = set(card_prev.get("in_transit", []))
        current_in_transit = set(in_transit)
        new_in_transit = current_in_transit - prev_in_transit
        
        if new_ready or new_in_transit:
            has_changes = True
            
        card_results.append({
            "name": name,
            "total": total,
            "ready": ready,
            "in_transit": in_transit,
            "new_ready": list(new_ready),
            "new_in_transit": list(new_in_transit)
        })

    # Output to console
    print("\n--- GVPL Holds Summary ---")
    for res in card_results:
        print(f"[{res['name']}] Total Holds: {res['total']} | In Transit: {len(res['in_transit'])} | Ready for Pickup: {len(res['ready'])}")
        if res['in_transit']:
            for t in res['in_transit']:
                print(f"  🚚 {t}")
        if res['ready']:
            for r in res['ready']:
                print(f"  ✅ {r}")

    if has_changes or args.force_notify:
        report_lines = ["📚 *GVPL Library Holds Report*\n"]
        for res in card_results:
            name = res['name']
            report_lines.append(f"👤 *{name}'s Account*:")
            report_lines.append(f"Total Holds: {res['total']} | In Transit: {len(res['in_transit'])} | Ready: {len(res['ready'])}")
            
            if res['new_ready']:
                report_lines.append("  ✅ *NEW Ready for Pickup:*")
                for r in res['new_ready']:
                    report_lines.append(f"  • {r}")
            elif res['ready']:
                report_lines.append("  ✅ *Ready for Pickup:*")
                for r in res['ready']:
                    report_lines.append(f"  • {r}")
                    
            if res['new_in_transit']:
                report_lines.append("  🚚 *NEW In Transit:*")
                for t in res['new_in_transit']:
                    report_lines.append(f"  • {t}")
            elif res['in_transit']:
                report_lines.append("  🚚 *In Transit:*")
                for t in res['in_transit']:
                    report_lines.append(f"  • {t}")
            report_lines.append("")

        notification_body = "\n".join(report_lines).strip()
        
        channels = creds.get("channels", None)
        if channels is not None:
            if "desktop" in channels:
                notify_desktop("📚 GVPL Library Holds Update", notification_body)
            if "whatsapp" in channels:
                send_whatsapp_notifications(creds, notification_body)
            if "sms" in channels:
                send_sms_notifications(creds, notification_body)
        else:
            notify_desktop("📚 GVPL Library Holds Update", notification_body)
            send_whatsapp_notifications(creds, notification_body)
        
    if not args.dry_run:
        save_current_state(args.state, current_state)

if __name__ == "__main__":
    main()
