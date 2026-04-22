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
# GEMINI (for fast voice responses)
# ═══════════════════════════════════════════
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"  # Fast + 15 RPM free

# ═══════════════════════════════════════════
# CLAUDE CODE CLI (for coding/heavy tasks — uses your Max plan)
# ═══════════════════════════════════════════
CLAUDE_CLI_PATH = os.environ.get("CLAUDE_CLI_PATH", "claude")  # Path to claude CLI

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
AGENT_TOKEN = os.environ.get("AGENT_TOKEN", "sam-secret-2026")

# ═══════════════════════════════════════════
# BOT PERSONALITY (system prompt is built dynamically in brain.py)
# ═══════════════════════════════════════════
BOT_NAME = "SAM"
WAKE_WORD = "sam"

# ═══════════════════════════════════════════
# LOCATION (for weather, news, etc.)
# ═══════════════════════════════════════════
DEFAULT_CITY = "Delhi"  # Change to your city

# ═══════════════════════════════════════════
# CONVERSATION SETTINGS
# ═══════════════════════════════════════════
CONVERSATION_TIMEOUT = 10
