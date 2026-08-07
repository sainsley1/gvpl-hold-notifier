# 📚 GVPL Hold Notifier

Automated library hold notification tool for the Greater Victoria Public Library (GVPL / SirsiDynix Enterprise catalog).

Uses headless Firefox browser automation to bypass Cloudflare WAF / JS proof-of-work security checks, logs into multi-patron accounts, tracks active holds (`In Transit`, `Ready for Pickup`), and dispatches instant updates via **Desktop Notifications** (`notify-send`) and **WhatsApp** (Twilio / CallMeBot).

---

## ⚡ Features

- 🔑 **Multi-Patron Support**: Track multiple household library cards in a single run.
- 🛡️ **Cloudflare & WAF Bypass**: Uses Selenium with headless Firefox to complete dynamic challenge rendering automatically.
- 📊 **Smart State Preservation**: Intelligently tracks state diffs in `~/.config/library/holds_state.json` to prevent duplicate alerts.
- 🚚 **Status Tracking**: Categorizes holds by `Ready for Pickup` (`BEING HELD`) and `In Transit`.
- 📱 **Multi-Channel Dispatch**: Sends alerts via Linux desktop notifications (`notify-send`) and WhatsApp messages via Twilio API or CallMeBot.
- ⏰ **Systemd & Cron Ready**: Included systemd user service and timer unit files for automated background checking.

---

## 🚀 Installation & Setup

### 1. Requirements

Ensure Firefox and `geckodriver` (or `selenium`) are installed:

```bash
pip install -r requirements.txt
```

### 2. Configuration

Copy `credentials.example.json` to `~/.config/library/credentials.json`:

```bash
mkdir -p ~/.config/library
cp credentials.example.json ~/.config/library/credentials.json
nano ~/.config/library/credentials.json
```

Add your library card barcodes, PINs, and optional WhatsApp API credentials:

```json
{
  "cards": [
    {
      "name": "Seth",
      "barcode": "29066104123458",
      "pin": "1234"
    }
  ],
  "twilio_account_sid": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "twilio_auth_token": "your_auth_token",
  "twilio_from_number": "whatsapp:+14155238886",
  "twilio_to_numbers": ["+16045550199"]
}
```

---

## 🧪 Usage

### Manual Execution

```bash
python3 check_holds.py
```

### Command Line Options

```text
usage: check_holds.py [-h] [--config CONFIG] [--state STATE] [--force-notify] [--dry-run]

options:
  --config CONFIG  Path to credentials JSON file (default: ~/.config/library/credentials.json)
  --state STATE    Path to state JSON file (default: ~/.config/library/holds_state.json)
  --force-notify   Send notification regardless of state changes
  --dry-run        Perform check without updating state file
```

---

## ⏰ Automated Background Schedule (Systemd User Service)

To run the notifier automatically in the background every 2 hours:

```bash
mkdir -p ~/.config/systemd/user
cp systemd/gvpl-holds.service systemd/gvpl-holds.timer ~/.config/systemd/user/

systemctl --user daemon-reload
systemctl --user enable --now gvpl-holds.timer
systemctl --user status gvpl-holds.timer
```

---

## 📁 Repository Structure

```text
gvpl-hold-notifier/
├── check_holds.py            # Main executable script
├── credentials.example.json  # Configuration template
├── requirements.txt          # Python dependencies
├── README.md                 # Project documentation
└── systemd/                  # Systemd service & timer unit files
    ├── gvpl-holds.service
    └── gvpl-holds.timer
```
