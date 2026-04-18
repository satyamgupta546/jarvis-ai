"""
╔══════════════════════════════════════════════╗
║          J.A.R.V.I.S  AI  ASSISTANT          ║
║     Just A Rather Very Intelligent System     ║
╚══════════════════════════════════════════════╝

Cloud-hosted AI assistant.
Open the URL on your phone → say "Hey Jarvis" → talk.

Usage:
    python main.py
"""

import sys
import uvicorn
from config import SERVER_HOST, SERVER_PORT, GEMINI_API_KEY

def main():
    if not GEMINI_API_KEY:
        print("ERROR: Set GEMINI_API_KEY in config.py or as environment variable")
        sys.exit(1)

    print("╔══════════════════════════════════════════════╗")
    print("║          J.A.R.V.I.S  AI  ASSISTANT          ║")
    print("╚══════════════════════════════════════════════╝")
    print(f"\n  Server: http://0.0.0.0:{SERVER_PORT}")
    print(f"  Open this URL on your phone (same WiFi)")
    print(f"  Then just say: 'Hey Jarvis'\n")

    uvicorn.run(
        "server:app",
        host=SERVER_HOST,
        port=SERVER_PORT,
        log_level="info",
    )

if __name__ == "__main__":
    main()
