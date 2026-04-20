"""Jarvis Task Parser - Extracts all command tags from AI responses."""

import re
import datetime


def parse_commands(response: str) -> list[dict]:
    """Parse AI response for command tags. Returns list of actions."""
    commands = []

    # ── Media ──
    for name in re.findall(r"\[PLAY_SONG:\s*(.+?)\]", response):
        url = f"https://www.youtube.com/results?search_query={name.strip().replace(' ', '+')}"
        commands.append({"type": "play_song", "name": name.strip(), "url": url})

    for genre in re.findall(r"\[RADIO:\s*(.+?)\]", response):
        commands.append({"type": "radio", "genre": genre.strip()})

    for app in re.findall(r"\[PLAY_STORE:\s*(.+?)\]", response):
        url = f"https://play.google.com/store/search?q={app.strip().replace(' ', '+')}&c=apps"
        commands.append({"type": "play_store", "app": app.strip(), "url": url})

    # ── Information (need server-side fetch) ──
    weather_matches = re.findall(r"\[WEATHER(?::\s*(.+?))?\]", response)
    for city in weather_matches:
        commands.append({"type": "weather", "city": city.strip() if city else ""})

    news_matches = re.findall(r"\[NEWS(?::\s*(.+?))?\]", response)
    for topic in news_matches:
        commands.append({"type": "news", "topic": topic.strip() if topic else ""})

    for query in re.findall(r"\[WEB_SEARCH:\s*(.+?)\]", response):
        url = f"https://www.google.com/search?q={query.strip().replace(' ', '+')}"
        commands.append({"type": "web_search", "query": query.strip(), "url": url})

    for url in re.findall(r"\[OPEN_URL:\s*(.+?)\]", response):
        commands.append({"type": "open_url", "url": url.strip()})

    if "[GET_TIME]" in response:
        now = datetime.datetime.now()
        commands.append({"type": "time", "text": now.strftime("It is %A, %B %d, %Y. The time is %I:%M %p.")})

    # ── Timer & Reminder (handled on phone browser) ──
    for secs in re.findall(r"\[TIMER:\s*(\d+)\]", response):
        commands.append({"type": "timer", "seconds": int(secs)})

    for match in re.findall(r"\[REMINDER:\s*(\d+),\s*(.+?)\]", response):
        commands.append({"type": "reminder", "minutes": int(match[0]), "text": match[1].strip()})

    # ── Smart Home ──
    for match in re.findall(r"\[DEVICE:\s*(.+?),\s*(ON|OFF)\]", response, re.IGNORECASE):
        commands.append({"type": "device", "device_id": match[0].strip(), "action": match[1].strip().upper()})

    # ── Desktop Agent ──
    for path in re.findall(r"\[READ_FILE:\s*(.+?)\]", response):
        commands.append({"type": "read_file", "path": path.strip()})

    for path in re.findall(r"\[LIST_FILES:\s*(.+?)\]", response):
        commands.append({"type": "list_files", "path": path.strip()})

    for app in re.findall(r"\[OPEN_APP:\s*(.+?)\]", response):
        commands.append({"type": "open_app", "app": app.strip()})

    if "[SYSTEM_INFO]" in response:
        commands.append({"type": "system_info"})

    # [CLAUDE_CODE: prompt] — heavy coding via Claude CLI
    for prompt in re.findall(r"\[CLAUDE_CODE:\s*(.+?)\]", response, re.DOTALL):
        commands.append({"type": "claude_code", "prompt": prompt.strip()})

    # ── Optimus Widget Creation ──
    for match in re.findall(r"\[CREATE_SPR:\s*(.+?)\]", response):
        parts = [p.strip() for p in match.split("|")]
        cmd = {"type": "create_spr", "title": parts[0], "products": parts[1] if len(parts) > 1 else ""}
        if len(parts) > 2:
            cmd["rows"] = int(parts[2])
        if len(parts) > 3:
            cmd["optimized"] = parts[3].lower() == "true"
        commands.append(cmd)

    for match in re.findall(r"\[CREATE_BANNER:\s*(.+?)\]", response):
        parts = [p.strip() for p in match.split("|")]
        commands.append({"type": "create_banner", "title": parts[0], "mode": parts[1] if len(parts) > 1 else "scroll"})

    for match in re.findall(r"\[CREATE_MASTHEAD:\s*(.+?)\]", response):
        parts = [p.strip() for p in match.split("|")]
        commands.append({"type": "create_masthead", "slug": parts[0], "variant": parts[1] if len(parts) > 1 else "primary"})

    if "[LIST_WIDGETS]" in response:
        commands.append({"type": "list_widgets"})

    if "[LIST_REQUESTS]" in response:
        commands.append({"type": "list_requests"})

    # ── Code / Project creation ──
    for match in re.findall(r"\[WRITE_FILE:\s*(.+?)\]", response):
        commands.append({"type": "write_file", "path": match.strip()})

    for match in re.findall(r"\[RUN:\s*(.+?)\]", response):
        commands.append({"type": "run_command", "command": match.strip()})

    # Extract code blocks and attach to WRITE_FILE commands
    code_blocks = re.findall(r"```(?:\w+)?\n(.*?)```", response, re.DOTALL)
    write_cmds = [c for c in commands if c["type"] == "write_file"]
    for i, cmd in enumerate(write_cmds):
        if i < len(code_blocks):
            cmd["content"] = code_blocks[i]

    # ── Office / Slack ──
    for ch in re.findall(r"\[SLACK_READ:\s*(.+?)\]", response):
        commands.append({"type": "slack_read", "channel": ch.strip()})

    for match in re.findall(r"\[SLACK_SEND:\s*(.+?),\s*(.+?)\]", response):
        commands.append({"type": "slack_send", "channel": match[0].strip(), "message": match[1].strip()})

    for q in re.findall(r"\[SLACK_SEARCH:\s*(.+?)\]", response):
        commands.append({"type": "slack_search", "query": q.strip()})

    for name in re.findall(r"\[PROJECT_INFO:\s*(.+?)\]", response):
        commands.append({"type": "project_info", "name": name.strip()})

    if "[PENDING_TASKS]" in response:
        commands.append({"type": "pending_tasks"})

    return commands


def strip_command_tags(text: str) -> str:
    """Remove ALL command tags so they're not spoken aloud."""
    patterns = [
        r"\[PLAY_SONG:\s*.+?\]",
        r"\[RADIO:\s*.+?\]",
        r"\[PLAY_STORE:\s*.+?\]",
        r"\[WEATHER(?::\s*.+?)?\]",
        r"\[NEWS(?::\s*.+?)?\]",
        r"\[WEB_SEARCH:\s*.+?\]",
        r"\[OPEN_URL:\s*.+?\]",
        r"\[GET_TIME\]",
        r"\[TIMER:\s*\d+\]",
        r"\[REMINDER:\s*\d+,\s*.+?\]",
        r"\[DEVICE:\s*.+?,\s*(?:ON|OFF)\]",
        r"\[READ_FILE:\s*.+?\]",
        r"\[LIST_FILES:\s*.+?\]",
        r"\[OPEN_APP:\s*.+?\]",
        r"\[SYSTEM_INFO\]",
        r"\[SLACK_READ:\s*.+?\]",
        r"\[SLACK_SEND:\s*.+?,\s*.+?\]",
        r"\[SLACK_SEARCH:\s*.+?\]",
        r"\[PROJECT_INFO:\s*.+?\]",
        r"\[PENDING_TASKS\]",
        r"\[CLAUDE_CODE:\s*.+?\]",
        r"\[CREATE_SPR:\s*.+?\]",
        r"\[CREATE_BANNER:\s*.+?\]",
        r"\[CREATE_MASTHEAD:\s*.+?\]",
        r"\[LIST_WIDGETS\]",
        r"\[LIST_REQUESTS\]",
        r"\[WRITE_FILE:\s*.+?\]",
        r"\[RUN:\s*.+?\]",
        r"```(?:\w+)?\n.*?```",
    ]
    for p in patterns:
        text = re.sub(p, "", text, flags=re.IGNORECASE)
    return text.strip()


# ── Command categorization ──

DESKTOP_TYPES = {"read_file", "list_files", "open_app", "system_info", "write_file", "run_command", "claude_code"}
DATA_FETCH_TYPES = {"weather", "news", "slack_read", "slack_search", "project_info", "pending_tasks",
                     "create_spr", "create_banner", "create_masthead", "list_widgets", "list_requests"}
PHONE_TYPES = {"play_song", "radio", "play_store", "web_search", "open_url", "time", "timer", "reminder"}
DEVICE_TYPES = {"device"}
OFFICE_ACTION_TYPES = {"slack_send"}  # Actions that execute but don't return data to Gemini


def get_commands_by_category(commands):
    """Split commands into categories."""
    return {
        "phone": [c for c in commands if c["type"] in PHONE_TYPES],
        "device": [c for c in commands if c["type"] in DEVICE_TYPES],
        "data": [c for c in commands if c["type"] in DATA_FETCH_TYPES],
        "desktop": [c for c in commands if c["type"] in DESKTOP_TYPES],
    }
