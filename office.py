"""SAM Office Module - Slack integration + Project knowledge"""

import json
import urllib.request
import urllib.parse
from config import SLACK_BOT_TOKEN


def _slack_api(method: str, params: dict = None) -> dict:
    """Call Slack Web API."""
    if not SLACK_BOT_TOKEN:
        return {"ok": False, "error": "Slack token not configured. Add SLACK_BOT_TOKEN in config."}

    url = f"https://slack.com/api/{method}"
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json; charset=utf-8",
    }

    data = json.dumps(params or {}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read())
    except Exception as e:
        return {"ok": False, "error": str(e)}


def slack_find_channel(name: str) -> str | None:
    """Find channel ID by name."""
    name = name.lower().replace("#", "").replace(" ", "_")

    # Search public + private channels
    for channel_type in ["public_channel", "private_channel"]:
        result = _slack_api("conversations.list", {
            "types": channel_type,
            "limit": 200,
            "exclude_archived": True,
        })
        if result.get("ok"):
            for ch in result.get("channels", []):
                if ch["name"].lower() == name:
                    return ch["id"]
    return None


def slack_read_channel(channel_name: str, count: int = 10) -> dict:
    """Read latest messages from a Slack channel."""
    channel_id = slack_find_channel(channel_name)
    if not channel_id:
        return {"status": "error", "error": f"Channel '{channel_name}' not found"}

    result = _slack_api("conversations.history", {
        "channel": channel_id,
        "limit": count,
    })

    if not result.get("ok"):
        return {"status": "error", "error": result.get("error", "Unknown error")}

    messages = []
    for msg in result.get("messages", []):
        # Get user info
        user_info = _slack_api("users.info", {"user": msg.get("user", "")})
        user_name = "Unknown"
        if user_info.get("ok"):
            user_name = user_info["user"].get("real_name", user_info["user"].get("name", "Unknown"))

        messages.append({
            "from": user_name,
            "text": msg.get("text", "")[:500],  # Limit text length
            "ts": msg.get("ts", ""),
        })

    return {"status": "ok", "channel": channel_name, "messages": messages}


def slack_send_message(channel_name: str, text: str) -> dict:
    """Send a message to a Slack channel."""
    channel_id = slack_find_channel(channel_name)
    if not channel_id:
        return {"status": "error", "error": f"Channel '{channel_name}' not found"}

    result = _slack_api("chat.postMessage", {
        "channel": channel_id,
        "text": text,
    })

    if result.get("ok"):
        return {"status": "ok", "message": f"Message sent to #{channel_name}"}
    return {"status": "error", "error": result.get("error", "Failed to send")}


def slack_search(query: str) -> dict:
    """Search Slack messages."""
    result = _slack_api("search.messages", {
        "query": query,
        "count": 5,
    })

    if not result.get("ok"):
        return {"status": "error", "error": result.get("error", "Search failed")}

    matches = []
    for msg in result.get("messages", {}).get("matches", []):
        matches.append({
            "channel": msg.get("channel", {}).get("name", "?"),
            "from": msg.get("username", "?"),
            "text": msg.get("text", "")[:300],
        })

    return {"status": "ok", "query": query, "results": matches}


# ── Project Knowledge Base ──
PROJECTS = {
    "optimus": {
        "name": "Optimus (Homepage CMS)",
        "desc": "ApnaMart app ka mobile UI builder. Drag-drop widgets (SPR, Banner, Masthead). Maker-Checker approval workflow.",
        "tech": "React 19, Express 5, Prisma/SQLite, Vite, Vercel",
        "status": "Live — Manoj actively using. Vercel pe hosted.",
        "path": "/Users/satyam/Desktop/code/optimus",
    },
    "price_benchmark": {
        "name": "SAM (Price Benchmark)",
        "desc": "Competitor price tracker — Blinkit, Zepto, JioMart, Flipkart Minutes, Instamart se scrape. Replaced ₹3L/month Anakin.",
        "tech": "FastAPI, Playwright, React, SSE, BigQuery",
        "status": "Running daily cron. 4 cities. 98.9% coverage.",
        "path": "/Users/satyam/Desktop/code/Price benchmark",
    },
    "manufacture": {
        "name": "Manufacturer Database",
        "desc": "DMart + BigBasket se vendor/manufacturer data scraping. 10,854 DMart + 24,153 BigBasket products.",
        "tech": "Python, Playwright, Google Apps Script, Google Sheets",
        "status": "Complete. Normalization done.",
        "path": "/Users/satyam/Desktop/code/manufacture",
    },
    "image_verification": {
        "name": "Damaged Product Image Verification",
        "desc": "Audit images verify karta hai — AI (Claude Vision) + rule-based validation.",
        "tech": "Python, Claude Vision API, Metabase, Pandas",
        "status": "Script ready. Rohit ko manual verify karne bola.",
        "path": "/Users/satyam/Desktop/code/rohit jain image verification",
    },
    "istre3": {
        "name": "istrE3 (Laundry Platform)",
        "desc": "On-demand clothes ironing service. 22-state order machine, GPS geofencing, QR bag tracking.",
        "tech": "NestJS, Prisma/PostgreSQL, Redis/BullMQ, Socket.IO, Firebase FCM, Docker",
        "status": "Production-ready architecture.",
        "path": "/Users/satyam/Desktop/code/istrE3",
    },
    "admin_dashboard": {
        "name": "istrE3 Admin Dashboard",
        "desc": "Laundry service ka admin panel — orders, riders, hubs, users, maps.",
        "tech": "React 19, Vite, Tailwind, Supabase, Leaflet Maps",
        "status": "Partially built. Some pages missing.",
        "path": "/Users/satyam/Desktop/code/admin-dashboard",
    },
    "subscription": {
        "name": "Milk Subscription Engine",
        "desc": "ApnaMart milk subscription — daily delivery + UPI autopay. Pre-generated 30-day calendar.",
        "tech": "Next.js 14, React 18, Prisma/SQLite, Zod, node-cron",
        "status": "Functional with API routes and cron jobs.",
        "path": "/Users/satyam/Desktop/code/subscription model",
    },
    "daily_milk": {
        "name": "Daily Milk Delights (UI Prototype)",
        "desc": "Milk subscription ka polished mobile-first UI. 47+ Amul products, shadcn/ui.",
        "tech": "React 18, TypeScript, Vite, shadcn/ui, TanStack Query",
        "status": "UI complete. Mock data, no real backend.",
        "path": "/Users/satyam/Desktop/code/daily-milk-delights-main",
    },
    "ai_photos": {
        "name": "AI Photo Studio",
        "desc": "Photo transformation — upload photo, select style (Ghibli, Anime, etc.), AI converts.",
        "tech": "Next.js 16, TypeScript, Hugging Face FLUX model",
        "status": "Working web app.",
        "path": "/Users/satyam/Desktop/code/ai-photos",
    },
}

PENDING_TASKS = [
    {"from": "Radhika Maheshwari", "task": "Store-to-App: 3-day follow-up message for non-ordering customers", "priority": "Medium"},
    {"from": "Rohit Jain", "task": "Damaged product image analysis — waiting for manual verification", "priority": "Low (waiting)"},
    {"from": "Ayush Umrao", "task": "Price Benchmark — host on Vercel (Playwright heavy issue)", "priority": "Medium"},
    {"from": "Ayush Umrao", "task": "Optimus — backend hosted on Forge? (unanswered)", "priority": "Low"},
    {"from": "Diksha Chandna", "task": "AMS bulk update/delete automation", "priority": "Medium"},
    {"from": "Sapna Meena", "task": "WhatsApp polls response automation", "priority": "Medium"},
    {"from": "Sapna Meena", "task": "Daily metrics automation (23 online + 1 offline stores)", "priority": "High"},
    {"from": "Sapna Meena", "task": "Shop Now CTA button for community messages", "priority": "Low"},
]


def get_project_info(name: str) -> dict:
    """Get info about a specific project."""
    name_lower = name.lower().replace(" ", "_").replace("-", "_")
    for key, proj in PROJECTS.items():
        if name_lower in key or name_lower in proj["name"].lower():
            return {"status": "ok", "project": proj}
    return {"status": "error", "error": f"Project '{name}' not found. Available: {', '.join(p['name'] for p in PROJECTS.values())}"}


def get_pending_tasks() -> dict:
    """Get list of pending office tasks."""
    return {"status": "ok", "tasks": PENDING_TASKS}


def get_all_projects_summary() -> str:
    """Short summary of all projects for system prompt."""
    lines = []
    for key, p in PROJECTS.items():
        lines.append(f"  - {p['name']}: {p['status']}")
    return "\n".join(lines)
