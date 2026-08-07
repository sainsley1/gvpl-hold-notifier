# 📚 GVPL Hold Notifier

Automated library hold notification tool for the Greater Victoria Public Library (GVPL / SirsiDynix Enterprise catalog).

Uses headless Firefox browser automation to bypass Cloudflare WAF / JS proof-of-work security checks, logs into multi-patron accounts, tracks active holds (`In Transit`, `Ready for Pickup`), and dispatches instant updates via **Desktop Notifications** (`notify-send`), **Twilio WhatsApp**, and **Twilio SMS**.

---

## ⚡ Features

- 🧙‍♂️ **Interactive Guided Installer**: Customizes patron cards, notification channels (Desktop, WhatsApp, SMS), and API credentials upon installation.
- 🔑 **Multi-Patron Support**: Track multiple household library cards configured in `~/.config/library/credentials.json`.
- 📲 **Flexible Notifications**: Send alerts via Linux Desktop Notifications, WhatsApp, and/or SMS to multiple recipients.
- 🔒 **Zero Hardcoded Credentials**: All patron names, library card barcodes, PINs, and Twilio API keys are dynamically loaded from configuration.
- 🛡️ **Cloudflare & WAF Bypass**: Uses Selenium with headless Firefox to complete dynamic challenge rendering automatically.
- 📊 **Smart State Preservation**: Intelligently tracks state diffs in `~/.config/library/holds_state.json` to prevent duplicate alerts.
- 🚚 **Status Tracking**: Categorizes holds by `Ready for Pickup` (`BEING HELD`) and `In Transit`.
- ⏰ **Automated 30-Minute Schedule**: Automated background checking via systemd user timer every 30 minutes.

---

## 🚀 One-Step Automated Installation & Interactive Setup

Download or clone the source repository, then run the included installer:

```bash
chmod +x install.sh
./install.sh
```

The installer automatically:
1. Installs Python dependencies (`pip install -r requirements.txt`).
2. Launches an interactive setup wizard (`setup_wizard.py`) to prompt for:
   - Number of patrons/library cards & credentials (names, barcodes, PINs)
   - Preferred notification channels (Desktop, WhatsApp, SMS)
   - Notification recipient phone numbers and Twilio credentials
3. Saves custom configuration to `~/.config/library/credentials.json`.
4. Installs and enables the `gvpl-holds.timer` systemd user service to run automatically **every 30 minutes**.

*(To skip the interactive wizard during automated deployment, pass `--non-interactive` to `./install.sh`)*.

---

## ⚙️ Configuration

You can re-run the interactive wizard at any time:

```bash
python3 setup_wizard.py
```

Or manually edit your configuration file at `~/.config/library/credentials.json`:

```json
{
  "cards": [
    {
      "name": "Patron Name 1",
      "barcode": "29066123456789",
      "pin": "1234"
    },
    {
      "name": "Patron Name 2",
      "barcode": "29066987654321",
      "pin": "5678"
    }
  ],
  "channels": [
    "desktop",
    "whatsapp",
    "sms"
  ],
  "twilio_account_sid": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "twilio_auth_token": "your_twilio_auth_token",
  "twilio_from_number": "+18005550199",
  "twilio_whatsapp_from": "whatsapp:+14155238886",
  "twilio_to_numbers": [
    "+16045550199",
    "+12505550188"
  ]
}
```

---

## 🧪 Usage & Testing

### Run Manual Check

```bash
python3 check_holds.py
```

### Dry-Run (Preview Output Without Updating State)

```bash
python3 check_holds.py --dry-run
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

## ⏰ Systemd Timer Management

The systemd user timer runs background checks **every 30 minutes**:

```bash
# Check timer status
systemctl --user status gvpl-holds.timer

# View execution logs
journalctl --user -u gvpl-holds.service -f

# Manually trigger background run
systemctl --user start gvpl-holds.service
```

---

## 📁 Repository Structure

```text
gvpl-hold-notifier/
├── install.sh                # Automated installer with setup wizard prompt
├── setup_wizard.py           # Interactive configuration CLI wizard
├── check_holds.py            # Main hold checker & notification script
├── credentials.example.json  # Configuration template
├── requirements.txt          # Python dependencies
├── README.md                 # Project documentation
└── systemd/                  # Systemd service & timer unit files
    ├── gvpl-holds.service
    └── gvpl-holds.timer
```
