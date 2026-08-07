#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$HOME/.config/library"
CREDENTIALS_FILE="$CONFIG_DIR/credentials.json"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"

echo "=========================================="
echo "  GVPL Hold Notifier Installation Script  "
echo "=========================================="

# 1. Verify Prerequisites
echo "--> Checking system dependencies..."
if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 is required but not installed." >&2
    exit 1
fi

if ! command -v firefox >/dev/null 2>&1; then
    echo "WARNING: Firefox browser is recommended for headless Selenium automation." >&2
fi

# 2. Make check_holds.py executable
chmod +x "$SCRIPT_DIR/check_holds.py"

# 3. Install Python Dependencies
echo "--> Installing Python dependencies from requirements.txt..."
python3 -m pip install -r "$SCRIPT_DIR/requirements.txt" --user

# 4. Provision Configuration
echo "--> Setting up configuration directory..."
mkdir -p "$CONFIG_DIR"

if [[ ! -f "$CREDENTIALS_FILE" ]]; then
    echo "--> Copying credentials template to $CREDENTIALS_FILE..."
    cp "$SCRIPT_DIR/credentials.example.json" "$CREDENTIALS_FILE"
    echo "⚠️  Action required: Edit $CREDENTIALS_FILE and add your library card barcode(s) and PIN(s)."
else
    echo "--> Found existing credentials file at $CREDENTIALS_FILE."
fi

# 5. Install Systemd User Service & 30-Minute Timer
if command -v systemctl >/dev/null 2>&1; then
    echo "--> Installing systemd user service and 30-minute timer..."
    mkdir -p "$SYSTEMD_USER_DIR"

    # Generate systemd service unit with absolute path
    cat <<EOF > "$SYSTEMD_USER_DIR/gvpl-holds.service"
[Unit]
Description=GVPL Library Holds Notifier Service
After=network.target network-online.target

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 $SCRIPT_DIR/check_holds.py
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
EOF

    # Copy 30-minute timer unit
    cp "$SCRIPT_DIR/systemd/gvpl-holds.timer" "$SYSTEMD_USER_DIR/gvpl-holds.timer"

    systemctl --user daemon-reload
    systemctl --user enable --now gvpl-holds.timer

    echo "--> Systemd timer enabled and started (runs every 30 minutes)."
    echo "    Check timer status: systemctl --user status gvpl-holds.timer"
fi

echo ""
echo "=========================================="
echo "  Installation Complete!                 "
echo "=========================================="
echo "Next Steps:"
echo "1. Edit credentials file: nano ~/.config/library/credentials.json"
echo "2. Run manual test check: python3 $SCRIPT_DIR/check_holds.py --dry-run"
echo "=========================================="
