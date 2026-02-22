#!/usr/bin/env bash
# =============================================================================
# reset_db.sh — Wipe and reinitialise the DTC League database on AWS EC2.
#
# Usage:
#   chmod +x reset_db.sh
#   ./reset_db.sh [--service <service-name>]
#
# Options:
#   --service <name>   systemd service name for the Flask app (default: dtc-league)
#
# What this script does:
#   1. Stops the Flask web service so the database file is not locked.
#   2. Runs init_db.py which:
#        a. Exports reference tables (systems, factions, seasons, etc.) to CSV.
#        b. Creates a timestamped backup of GPTLeague.db.
#        c. Deletes GPTLeague.db and creates a fresh one from schema.sql.
#        d. Reimports the reference table CSVs.
#        e. Cleans up temporary session files.
#   3. Restarts the web service.
#
# Requirements:
#   - Python 3 with flask, flask_session, bcrypt, plotly installed.
#   - The script must be run from the project root directory.
#   - The web service must be managed by systemd (or adjust the stop/start
#     commands below if you use a different process manager).
# =============================================================================

set -euo pipefail

SERVICE_NAME="dtc-league"

# Parse optional --service argument
while [[ $# -gt 0 ]]; do
    case "$1" in
        --service)
            SERVICE_NAME="$2"
            shift 2
            ;;
        *)
            echo "Unknown argument: $1"
            echo "Usage: $0 [--service <service-name>]"
            exit 1
            ;;
    esac
done

# Resolve the directory that contains this script (the project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================================"
echo "  DTC League — Database Reset"
echo "============================================================"
echo "  Project directory : $SCRIPT_DIR"
echo "  Web service name  : $SERVICE_NAME"
echo ""

# ------------------------------------------------------------------
# Step 1: Stop the web service
# ------------------------------------------------------------------
echo "[1/3] Stopping web service ($SERVICE_NAME)..."
if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
    sudo systemctl stop "$SERVICE_NAME"
    echo "  ✓ Service stopped"
else
    echo "  ⚠ Service '$SERVICE_NAME' is not running (or not found) — continuing anyway"
fi

# ------------------------------------------------------------------
# Step 2: Run the database initialisation script
# ------------------------------------------------------------------
echo ""
echo "[2/3] Running database initialisation..."
python3 init_db.py

# ------------------------------------------------------------------
# Step 3: Restart the web service
# ------------------------------------------------------------------
echo ""
echo "[3/3] Restarting web service ($SERVICE_NAME)..."
if systemctl list-unit-files --type=service 2>/dev/null | grep -q "^${SERVICE_NAME}.service"; then
    sudo systemctl start "$SERVICE_NAME"
    echo "  ✓ Service started"
    echo ""
    echo "  Service status:"
    sudo systemctl status "$SERVICE_NAME" --no-pager -l | head -20
else
    echo "  ⚠ Service '$SERVICE_NAME' not found in systemd."
    echo "    Start your Flask app manually, for example:"
    echo "      gunicorn --bind 0.0.0.0:8000 server:app"
fi

echo ""
echo "============================================================"
echo "  ✓ Database reset complete"
echo "============================================================"
