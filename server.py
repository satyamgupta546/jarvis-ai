"""SAM Web Server - Handles everything: phone UI, smart home, data fetching, desktop agent."""

import asyncio
import json
import uuid
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import HTMLResponse

BASE_DIR = Path(__file__).parent
from brain import SAMBrain
from tasks import parse_commands, strip_command_tags, get_commands_by_category
from smart_home import control_device
from services import get_weather, get_news, get_radio_url
from office import slack_read_channel, slack_send_message, slack_search, get_project_info, get_pending_tasks
from optimus_agent import quick_create_spr, create_collection_banner, create_masthead, list_widgets, list_requests
from config import BOT_NAME, AGENT_TOKEN

app = FastAPI(title=f"{BOT_NAME} AI Assistant")

# Lazy init — don't crash on startup
brain: SAMBrain | None = None

def get_brain() -> SAMBrain:
    global brain
    if brain is None:
        brain = SAMBrain()
    return brain

# ── Desktop Agent state ──
desktop_agent: WebSocket | None = None
agent_pending: dict[str, asyncio.Future] = {}


# ═══════════════════════════════════════════
# Phone UI
# ═══════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def home():
    with open(BASE_DIR / "templates" / "index.html", "r") as f:
        return HTMLResponse(content=f.read())


@app.get("/health")
async def health():
    return {"status": "ok", "bot": BOT_NAME, "desktop_agent": desktop_agent is not None}


@app.websocket("/ws")
async def phone_endpoint(ws: WebSocket):
    await ws.accept()
    await ws.send_text(json.dumps({
        "type": "connected",
        "bot": BOT_NAME,
        "agent_online": desktop_agent is not None,
    }))

    try:
        while True:
            data = await ws.receive_text()
            payload = json.loads(data)

            if payload.get("action") == "message":
                response = await process_command(payload["text"])
                await ws.send_text(json.dumps(response))

            elif payload.get("action") == "reset":
                await asyncio.to_thread(get_brain().reset_memory)
                await ws.send_text(json.dumps({
                    "type": "response", "text": "Memory cleared, sir. Fresh start.", "commands": [],
                }))
    except WebSocketDisconnect:
        pass


# ═══════════════════════════════════════════
# Command Processing (the brain of the server)
# ═══════════════════════════════════════════

async def process_command(user_text: str) -> dict:
    """Full pipeline: Gemini → parse → fetch data → smart home → desktop → final response."""

    # Step 1: Get initial Gemini response
    response = await asyncio.to_thread(get_brain().think, user_text)
    commands = parse_commands(response)
    cats = get_commands_by_category(commands)
    clean_text = strip_command_tags(response)

    # Step 2: Execute smart home device commands
    for cmd in cats["device"]:
        result = await asyncio.to_thread(control_device, cmd["device_id"], cmd["action"])
        if result["status"] == "error":
            clean_text += f"\n({result['message']})"

    # Step 2b: Execute office action commands (Slack send)
    office_actions = [c for c in commands if c["type"] == "slack_send"]
    for cmd in office_actions:
        result = await asyncio.to_thread(slack_send_message, cmd["channel"], cmd["message"])
        if result["status"] == "ok":
            clean_text += f"\n(#{cmd['channel']} mein message bhej diya)"

    # Step 3: Fetch real-time data (weather, news, Slack, projects) and feed back to Gemini
    data_results = await _fetch_data(cats["data"])

    # Step 4: Handle desktop agent commands
    desktop_results = await _handle_desktop(cats["desktop"])

    # Step 5: If we got any data/desktop results, ask Gemini to present them
    all_results = {**data_results, **desktop_results}
    phone_cmds = cats["phone"]

    if all_results:
        follow_up_text = "Here are the results:\n" + json.dumps(all_results, indent=2, ensure_ascii=False)
        follow_up_text += "\n\nPresent this information to the user naturally and concisely."

        follow_up = await asyncio.to_thread(get_brain().think, follow_up_text)
        follow_up_commands = parse_commands(follow_up)
        follow_up_cats = get_commands_by_category(follow_up_commands)

        clean_text = strip_command_tags(follow_up)
        phone_cmds = phone_cmds + follow_up_cats["phone"]

    # Step 6: Resolve radio URLs
    for cmd in phone_cmds:
        if cmd["type"] == "radio":
            radio = get_radio_url(cmd["genre"])
            cmd["url"] = radio["url"]
            cmd["name"] = radio["name"]

    return {"type": "response", "text": clean_text, "commands": phone_cmds}


async def _fetch_data(data_commands: list[dict]) -> dict:
    """Fetch weather, news, Slack, project info, etc. Returns combined results."""
    results = {}
    for cmd in data_commands:
        if cmd["type"] == "weather":
            results["weather"] = await asyncio.to_thread(get_weather, cmd.get("city", ""))
        elif cmd["type"] == "news":
            results["news"] = await asyncio.to_thread(get_news, cmd.get("topic", ""))
        elif cmd["type"] == "slack_read":
            results["slack"] = await asyncio.to_thread(slack_read_channel, cmd["channel"])
        elif cmd["type"] == "slack_search":
            results["slack_search"] = await asyncio.to_thread(slack_search, cmd["query"])
        elif cmd["type"] == "project_info":
            results["project"] = get_project_info(cmd["name"])
        elif cmd["type"] == "pending_tasks":
            results["pending_tasks"] = get_pending_tasks()
        elif cmd["type"] == "create_spr":
            results["optimus"] = await asyncio.to_thread(
                quick_create_spr, cmd["title"], cmd.get("products", "")
            )
        elif cmd["type"] == "create_banner":
            results["optimus"] = await asyncio.to_thread(
                create_collection_banner, cmd["title"], cmd["title"], cmd.get("mode", "scroll")
            )
        elif cmd["type"] == "create_masthead":
            results["optimus"] = await asyncio.to_thread(
                create_masthead, cmd["slug"], cmd.get("variant", "primary")
            )
        elif cmd["type"] == "list_widgets":
            results["optimus_widgets"] = await asyncio.to_thread(list_widgets)
        elif cmd["type"] == "list_requests":
            results["optimus_requests"] = await asyncio.to_thread(list_requests)
    return results


async def _handle_desktop(desktop_commands: list[dict]) -> dict:
    """Forward commands to desktop agent. Returns results."""
    if not desktop_commands:
        return {}

    if not desktop_agent:
        return {"desktop_error": "MacBook desktop agent is not connected. Run agent.py on your Mac."}

    results = {}
    for i, cmd in enumerate(desktop_commands):
        result = await send_to_agent(cmd)
        results[f"desktop_{i}"] = result
    return results


# ═══════════════════════════════════════════
# Desktop Agent WebSocket
# ═══════════════════════════════════════════

@app.websocket("/ws/agent")
async def agent_endpoint(ws: WebSocket, token: str = Query("")):
    global desktop_agent

    if token != AGENT_TOKEN:
        await ws.close(code=4001, reason="Invalid token")
        return

    await ws.accept()
    desktop_agent = ws
    print(f"[Agent] MacBook desktop agent connected")

    try:
        while True:
            data = await ws.receive_text()
            result = json.loads(data)
            request_id = result.get("id")
            if request_id and request_id in agent_pending:
                agent_pending[request_id].set_result(result)
    except WebSocketDisconnect:
        desktop_agent = None
        print(f"[Agent] MacBook desktop agent disconnected")


async def send_to_agent(command: dict) -> dict:
    if not desktop_agent:
        return {"status": "error", "error": "Desktop agent not connected"}

    request_id = str(uuid.uuid4())
    future = asyncio.get_event_loop().create_future()
    agent_pending[request_id] = future

    try:
        await desktop_agent.send_text(json.dumps({"id": request_id, **command}))
        result = await asyncio.wait_for(future, timeout=15)
        return result
    except asyncio.TimeoutError:
        return {"status": "error", "error": "MacBook agent timed out"}
    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        agent_pending.pop(request_id, None)
