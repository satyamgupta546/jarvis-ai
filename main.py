"""
╔══════════════════════════════════════════════╗
║          S.A.M  AI  ASSISTANT          ║
║     Smart Omni-Network Intelligence Core     ║
╚══════════════════════════════════════════════╝

Cloud-hosted AI assistant.
Open the URL on your phone → say "Hey SAM" → talk.

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
    print("║          S.A.M  AI  ASSISTANT          ║")
    print("╚══════════════════════════════════════════════╝")
    print(f"\n  Server: http://0.0.0.0:{SERVER_PORT}")
    print(f"  Open this URL on your phone (same WiFi)")
    print(f"  Then just say: 'Hey SAM'\n")

    uvicorn.run(
        "server:app",
        host=SERVER_HOST,
        port=SERVER_PORT,
        log_level="info",
    )

if __name__ == "__main__":
    main()
