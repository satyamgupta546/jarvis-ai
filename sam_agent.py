"""
╔══════════════════════════════════════════════╗
║        S.A.M  MACBOOK  AGENT             ║
║  Proactive Alerts | Scheduler | Gmail        ║
║  Sheet Analysis | Error Monitor | Quick Acts ║
╚══════════════════════════════════════════════╝

Usage:  python sam_agent.py
Runs in background on MacBook. Ctrl+C to stop.
"""

import os
import json
import time
import datetime
import threading
import subprocess
import schedule
import urllib.request
import urllib.parse
import gspread
from google.oauth2.service_account import Credentials
from pathlib import Path
from groq import Groq

# ── Load .env ──
_env = Path(__file__).parent / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

# ── Config ──
BOT_NAME = "SAM"
GROQ_KEY = os.environ.get("GROQ_API_KEY", "")
SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
GOOGLE_CREDS = Path(__file__).parent / "credentials" / "google-service-account.json"
LOGS_FILE = Path(__file__).parent / "sam_agent_logs.json"

# ── Groq (for summarization) ──
groq_client = Groq(api_key=GROQ_KEY) if GROQ_KEY else None

# ── Google Sheets ──
gc = None
if GOOGLE_CREDS.exists():
    try:
        creds = Credentials.from_service_account_file(
            str(GOOGLE_CREDS),
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        )
        gc = gspread.authorize(creds)
        print(f"[{BOT_NAME}] Google Sheets connected.")
    except Exception as e:
        print(f"[{BOT_NAME}] Google Sheets error: {e}")


# ═══════════════════════════════════════════
# 1. SLACK FUNCTIONS
# ═══════════════════════════════════════════

def slack_api(method: str, params: dict = None) -> dict:
    if not SLACK_TOKEN:
        return {"ok": False, "error": "No SLACK_BOT_TOKEN"}
    url = f"https://slack.com/api/{method}"
    headers = {"Authorization": f"Bearer {SLACK_TOKEN}", "Content-Type": "application/json; charset=utf-8"}
    data = json.dumps(params or {}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        return json.loads(urllib.request.urlopen(req, timeout=15).read())
    except Exception as e:
        return {"ok": False, "error": str(e)}


def read_slack_channel(channel_id: str, count: int = 10) -> list:
    result = slack_api("conversations.history", {"channel": channel_id, "limit": count})
    if not result.get("ok"):
        return []
    messages = []
    for msg in result.get("messages", []):
        user = slack_api("users.info", {"user": msg.get("user", "")})
        name = user.get("user", {}).get("real_name", "Unknown") if user.get("ok") else "Unknown"
        messages.append({"from": name, "text": msg.get("text", "")[:300], "ts": msg.get("ts", "")})
    return messages


def send_slack_message(channel_id: str, text: str) -> bool:
    result = slack_api("chat.postMessage", {"channel": channel_id, "text": text})
    return result.get("ok", False)


# ═══════════════════════════════════════════
# 2. GMAIL FUNCTIONS (via Claude CLI)
# ═══════════════════════════════════════════

def check_gmail(query: str = "is:unread") -> str:
    """Use Claude CLI to check Gmail (since Gmail MCP is in Claude)."""
    try:
        result = subprocess.run(
            ["claude", "-p", "--output-format", "text"],
            input=f"Check my Gmail for: {query}. List the sender, subject, and a 1-line summary for each. Max 5 emails.",
            capture_output=True, text=True, timeout=30,
        )
        return result.stdout.strip() if result.stdout else "No response"
    except Exception as e:
        return f"Gmail check failed: {e}"


# ═══════════════════════════════════════════
# 3. GOOGLE SHEETS FUNCTIONS
# ═══════════════════════════════════════════

def read_sheet(sheet_url: str, worksheet_name: str = None) -> dict:
    """Read a Google Sheet and return data."""
    if not gc:
        return {"status": "error", "error": "Google Sheets not connected"}
    try:
        sh = gc.open_by_url(sheet_url)
        ws = sh.worksheet(worksheet_name) if worksheet_name else sh.sheet1
        data = ws.get_all_records()
        return {
            "status": "ok",
            "sheet_name": sh.title,
            "worksheet": ws.title,
            "rows": len(data),
            "columns": list(data[0].keys()) if data else [],
            "sample": data[:5],
            "all_data": data,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def analyze_sheet(sheet_url: str, question: str = "summarize") -> str:
    """Read sheet and use Groq to analyze."""
    data = read_sheet(sheet_url)
    if data.get("status") == "error":
        return f"Sheet error: {data['error']}"

    summary = f"Sheet: {data['sheet_name']}, Rows: {data['rows']}, Columns: {data['columns']}"
    sample = json.dumps(data['sample'], indent=2, ensure_ascii=False)

    if not groq_client:
        return f"{summary}\nSample:\n{sample}"

    try:
        r = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Analyze this Google Sheet data. Reply in Hinglish. Be concise."},
                {"role": "user", "content": f"Sheet: {summary}\nSample data:\n{sample}\n\nQuestion: {question}"}
            ],
            max_tokens=300,
        )
        return r.choices[0].message.content
    except Exception as e:
        return f"Analysis failed: {e}"


def write_to_sheet(sheet_url: str, worksheet_name: str, row_data: list) -> dict:
    """Append a row to a Google Sheet."""
    if not gc:
        return {"status": "error", "error": "Google Sheets not connected"}
    try:
        sh = gc.open_by_url(sheet_url)
        ws = sh.worksheet(worksheet_name) if worksheet_name else sh.sheet1
        ws.append_row(row_data)
        return {"status": "ok", "message": f"Row added to {sh.title}/{ws.title}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ═══════════════════════════════════════════
# 4. PROACTIVE ALERTS
# ═══════════════════════════════════════════

def check_alerts():
    """Scan Slack and check for things that need attention."""
    print(f"\n[{BOT_NAME}] Checking alerts...")
    alerts = []

    # Check product_automation channel for unread mentions
    messages = read_slack_channel("C09T03GLXAL", 10)
    for msg in messages:
        text = msg.get("text", "").lower()
        if "satyam" in text or "U04GAFD7N4E" in text:
            # Check if recent (last 4 hours)
            try:
                msg_time = float(msg.get("ts", 0))
                if time.time() - msg_time < 14400:  # 4 hours
                    alerts.append(f"📩 {msg['from']}: {msg['text'][:100]}")
            except:
                pass

    if alerts:
        print(f"[{BOT_NAME}] {len(alerts)} alerts found!")
        for a in alerts:
            print(f"  {a}")
    else:
        print(f"[{BOT_NAME}] No alerts.")

    log_event("alert_check", {"alerts_count": len(alerts), "alerts": alerts})
    return alerts


# ═══════════════════════════════════════════
# 5. SCHEDULED TASKS
# ═══════════════════════════════════════════

def morning_summary():
    """9 AM daily summary."""
    print(f"\n{'='*50}")
    print(f"  {BOT_NAME} — MORNING SUMMARY — {datetime.datetime.now().strftime('%A, %B %d')}")
    print(f"{'='*50}")

    # Slack messages from last night
    messages = read_slack_channel("C09T03GLXAL", 15)
    recent = [m for m in messages if time.time() - float(m.get("ts", 0)) < 43200]  # Last 12 hours

    summary = f"*{BOT_NAME} Morning Summary* 🌅\n\n"

    if recent:
        summary += f"*Slack (#product_automation):*\n"
        for m in recent[:5]:
            summary += f"• {m['from']}: {m['text'][:80]}\n"
    else:
        summary += "No new Slack messages overnight.\n"

    summary += f"\n*Pending Tasks:*\n"
    summary += "• Radhika: 3-day follow-up message\n"
    summary += "• Diksha: AMS bulk update automation\n"
    summary += "• Sapna: Daily metrics automation\n"

    summary += f"\n— *{BOT_NAME}* 🤖 _by Satyam_"

    print(summary)
    log_event("morning_summary", {"messages_count": len(recent)})


def evening_report():
    """6 PM daily report."""
    print(f"\n{'='*50}")
    print(f"  {BOT_NAME} — EVENING REPORT — {datetime.datetime.now().strftime('%A, %B %d')}")
    print(f"{'='*50}")

    summary = f"*{BOT_NAME} Evening Report* 🌙\n\n"
    summary += f"*Date:* {datetime.datetime.now().strftime('%A, %B %d, %Y')}\n\n"

    # Check today's conversations
    conv_file = Path(__file__).parent / "conversations.json"
    today_count = 0
    if conv_file.exists():
        try:
            data = json.loads(conv_file.read_text())
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            today_count = sum(1 for c in data.get("conversations", []) if c.get("date") == today)
        except:
            pass

    summary += f"*Conversations today:* {today_count}\n"
    summary += f"\n— *{BOT_NAME}* 🤖 _by Satyam_"

    print(summary)
    log_event("evening_report", {"conversations_today": today_count})


# ═══════════════════════════════════════════
# 6. ERROR MONITORING
# ═══════════════════════════════════════════

def health_check():
    """Check if key services are running."""
    print(f"\n[{BOT_NAME}] Running health check...")
    results = {}

    # Check Render server
    try:
        req = urllib.request.urlopen("https://jarvis-ai-wsds.onrender.com/health", timeout=10)
        data = json.loads(req.read())
        results["render_server"] = "✅ Online"
    except:
        results["render_server"] = "❌ Down"

    # Check Optimus
    try:
        req = urllib.request.Request(
            "https://optimus-app-hazel.vercel.app/api/local/widgets?env=PROD",
            headers={"X-Optimus-User": "satyam.gupta@apnamart.in"}
        )
        resp = urllib.request.urlopen(req, timeout=10)
        results["optimus"] = "✅ Online"
    except:
        results["optimus"] = "❌ Down"

    # Check Google Sheets
    results["google_sheets"] = "✅ Connected" if gc else "❌ Not connected"

    # Check Groq
    results["groq_api"] = "✅ Connected" if GROQ_KEY else "❌ No key"

    for k, v in results.items():
        print(f"  {k}: {v}")

    log_event("health_check", results)
    return results


# ═══════════════════════════════════════════
# 7. QUICK ACTIONS
# ═══════════════════════════════════════════

def quick_daily_report(channel_id: str = "C09T03GLXAL"):
    """Send daily report to Slack."""
    morning_summary()
    # Could also send to Slack if bot token available


def quick_sheet_summary(sheet_url: str):
    """Quick sheet analysis."""
    return analyze_sheet(sheet_url, "Summarize this data — kya important hai, kya missing hai?")


def quick_remind(user_id: str, message: str):
    """Send a reminder to someone on Slack."""
    return send_slack_message(user_id, f"Reminder from {BOT_NAME} 🤖\n\n{message}\n\n_by Satyam_")


# ═══════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════

def log_event(event_type: str, data: dict):
    """Log agent events to JSON file."""
    logs = []
    if LOGS_FILE.exists():
        try:
            logs = json.loads(LOGS_FILE.read_text())
        except:
            logs = []

    logs.append({
        "timestamp": datetime.datetime.now().isoformat(),
        "event": event_type,
        "data": data,
    })

    # Keep last 200 events
    if len(logs) > 200:
        logs = logs[-200:]

    LOGS_FILE.write_text(json.dumps(logs, indent=2, ensure_ascii=False))


# ═══════════════════════════════════════════
# MAIN AGENT LOOP
# ═══════════════════════════════════════════

def main():
    print(f"\n{'='*50}")
    print(f"  {BOT_NAME} AGENT — MacBook Edition")
    print(f"  Proactive Alerts | Scheduler | Health Monitor")
    print(f"  Ctrl+C to stop")
    print(f"{'='*50}\n")

    # Initial health check
    health_check()

    # Schedule tasks
    schedule.every().day.at("09:00").do(morning_summary)
    schedule.every().day.at("18:00").do(evening_report)
    schedule.every(1).hours.do(check_alerts)
    schedule.every(3).hours.do(health_check)

    print(f"\n[{BOT_NAME}] Scheduled:")
    print(f"  • 9:00 AM — Morning Summary")
    print(f"  • 6:00 PM — Evening Report")
    print(f"  • Every 1 hour — Alert Check")
    print(f"  • Every 3 hours — Health Check")
    print(f"\n[{BOT_NAME}] Agent running...\n")

    log_event("agent_started", {"time": datetime.datetime.now().isoformat()})

    while True:
        try:
            schedule.run_pending()
            time.sleep(30)
        except KeyboardInterrupt:
            print(f"\n[{BOT_NAME}] Agent stopped.")
            log_event("agent_stopped", {"time": datetime.datetime.now().isoformat()})
            break
        except Exception as e:
            print(f"[{BOT_NAME}] Error: {e}")
            time.sleep(60)


if __name__ == "__main__":
    main()
