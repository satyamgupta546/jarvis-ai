"""
J.A.R.V.I.S - Configuration
Cloud-hosted AI assistant with smart home + desktop agent support.
"""

import os
from pathlib import Path

# Load .env file if it exists (for local development)
_env_file = Path(__file__).parent / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

# ═══════════════════════════════════════════
# SERVER SETTINGS
# ═══════════════════════════════════════════
SERVER_HOST = "0.0.0.0"
SERVER_PORT = int(os.environ.get("PORT", 8000))

# ═══════════════════════════════════════════
# CLAUDE (ANTHROPIC) SETTINGS
# ═══════════════════════════════════════════
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-20250514"  # Options: claude-sonnet-4-20250514, claude-opus-4-20250514

# ═══════════════════════════════════════════
# TUYA SMART HOME (SmartLife devices)
# ═══════════════════════════════════════════
# Setup guide:
#   1. Buy Tuya/SmartLife compatible switches (Wipro, Orient, Syska etc.)
#   2. Set them up in the SmartLife app on your phone
#   3. Go to iot.tuya.com → Create account → Create Cloud Project
#   4. Link your SmartLife app account to the project
#   5. Copy Access ID, Access Secret, and Device IDs below
#
TUYA_ACCESS_ID = os.environ.get("TUYA_ACCESS_ID", "")
TUYA_ACCESS_SECRET = os.environ.get("TUYA_ACCESS_SECRET", "")
TUYA_REGION = "in"  # India = "in", US = "us", EU = "eu", China = "cn"

# ═══════════════════════════════════════════
# SLACK INTEGRATION
# ═══════════════════════════════════════════
# Create a Slack app at api.slack.com → OAuth → Bot Token
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")

# ═══════════════════════════════════════════
# DESKTOP AGENT (runs on MacBook)
# ═══════════════════════════════════════════
AGENT_TOKEN = os.environ.get("AGENT_TOKEN", "jarvis-secret-2026")

# ═══════════════════════════════════════════
# BOT PERSONALITY (system prompt is built dynamically in brain.py)
# ═══════════════════════════════════════════
BOT_NAME = "Jarvis"
WAKE_WORD = "jarvis"

# ═══════════════════════════════════════════
# LOCATION (for weather, news, etc.)
# ═══════════════════════════════════════════
DEFAULT_CITY = "Delhi"  # Change to your city

# ═══════════════════════════════════════════
# CONVERSATION SETTINGS
# ═══════════════════════════════════════════
CONVERSATION_TIMEOUT = 10
