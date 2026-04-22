"""
╔══════════════════════════════════════════════╗
║       J.A.R.V.I.S  DESKTOP  AGENT           ║
║    Run this on your MacBook to give SAM   ║
║    access to files, apps, and system info.   ║
╚══════════════════════════════════════════════╝

Usage:
    python agent.py                          (connects to localhost:8000)
    python agent.py wss://your-server.com    (connects to cloud server)
"""

import asyncio
import json
import os
import sys
import subprocess
import platform
import psutil
import websockets

# ── Config ──
AGENT_TOKEN = "sam-secret-2026"
DEFAULT_SERVER = "ws://localhost:8000"

# Safety: max file size to read (500KB)
MAX_FILE_SIZE = 500_000

# Blocked paths (never read these)
BLOCKED_PATTERNS = [
    ".ssh", ".env", "credentials", "secrets", "password",
    ".aws", ".gcloud", "keychain", "token",
]


def is_safe_path(path: str) -> bool:
    """Check if a file path is safe to read."""
    lower = path.lower()
    return not any(blocked in lower for blocked in BLOCKED_PATTERNS)


def handle_command(data: dict) -> dict:
    """Execute a command and return the result."""
    request_id = data.get("id", "")
    cmd_type = data.get("type", "")

    try:
        if cmd_type == "read_file":
            return read_file(request_id, data["path"])

        elif cmd_type == "list_files":
            return list_files(request_id, data.get("path", "~"))

        elif cmd_type == "open_app":
            return open_app(request_id, data["app"])

        elif cmd_type == "system_info":
            return get_system_info(request_id)

        elif cmd_type == "write_file":
            return write_file(request_id, data["path"], data["content"])

        elif cmd_type == "run_command":
            return run_command(request_id, data["command"], data.get("cwd"))

        elif cmd_type == "create_project":
            return create_project(request_id, data["name"], data.get("files", {}))

        elif cmd_type == "claude_code":
            return run_claude_code(request_id, data["prompt"], data.get("cwd"))

        else:
            return {"id": request_id, "status": "error", "error": f"Unknown command: {cmd_type}"}

    except Exception as e:
        return {"id": request_id, "status": "error", "error": str(e)}


def read_file(request_id: str, path: str) -> dict:
    """Read a file and return its contents."""
    path = os.path.expanduser(path)

    if not is_safe_path(path):
        return {"id": request_id, "status": "error", "error": "Access denied: sensitive file"}

    if not os.path.exists(path):
        return {"id": request_id, "status": "error", "error": f"File not found: {path}"}

    if os.path.getsize(path) > MAX_FILE_SIZE:
        return {"id": request_id, "status": "error", "error": "File too large (max 500KB)"}

    with open(path, "r", errors="replace") as f:
        content = f.read()

    return {
        "id": request_id,
        "status": "ok",
        "type": "file_content",
        "path": path,
        "content": content,
        "size": len(content),
    }


def list_files(request_id: str, path: str) -> dict:
    """List files in a directory."""
    path = os.path.expanduser(path)

    if not os.path.isdir(path):
        return {"id": request_id, "status": "error", "error": f"Not a directory: {path}"}

    entries = []
    for name in sorted(os.listdir(path)):
        full = os.path.join(path, name)
        entry = {"name": name, "is_dir": os.path.isdir(full)}
        if not entry["is_dir"]:
            try:
                entry["size"] = os.path.getsize(full)
            except OSError:
                entry["size"] = 0
        entries.append(entry)

    return {
        "id": request_id,
        "status": "ok",
        "type": "file_list",
        "path": path,
        "entries": entries[:100],  # Max 100 entries
        "total": len(entries),
    }


def open_app(request_id: str, app_name: str) -> dict:
    """Open an application on macOS."""
    system = platform.system()
    if system == "Darwin":
        subprocess.Popen(["open", "-a", app_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif system == "Windows":
        subprocess.Popen(["start", app_name], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        subprocess.Popen([app_name.lower()], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return {"id": request_id, "status": "ok", "message": f"Opened {app_name}"}


def write_file(request_id: str, path: str, content: str) -> dict:
    """Write content to a file. Creates parent dirs if needed."""
    path = os.path.expanduser(path)

    if not is_safe_path(path):
        return {"id": request_id, "status": "error", "error": "Access denied: sensitive path"}

    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w") as f:
        f.write(content)

    return {
        "id": request_id,
        "status": "ok",
        "message": f"File written: {path}",
        "path": path,
        "size": len(content),
    }


def run_command(request_id: str, command: str, cwd: str = None) -> dict:
    """Run a shell command and return output. Timeout: 60 seconds."""
    cwd = os.path.expanduser(cwd) if cwd else None

    # Block dangerous commands
    dangerous = ["rm -rf /", "mkfs", "dd if=", "> /dev/", ":(){ :|:& };:"]
    if any(d in command for d in dangerous):
        return {"id": request_id, "status": "error", "error": "Dangerous command blocked"}

    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            timeout=60, cwd=cwd,
        )
        output = result.stdout[-5000:] if result.stdout else ""  # Last 5KB
        error = result.stderr[-2000:] if result.stderr else ""

        return {
            "id": request_id,
            "status": "ok" if result.returncode == 0 else "error",
            "returncode": result.returncode,
            "stdout": output,
            "stderr": error,
        }
    except subprocess.TimeoutExpired:
        return {"id": request_id, "status": "error", "error": "Command timed out (60s)"}
    except Exception as e:
        return {"id": request_id, "status": "error", "error": str(e)}


def create_project(request_id: str, name: str, files: dict) -> dict:
    """Create a project folder with multiple files.
    files = {"filename": "content", "subfolder/file.py": "content"}
    """
    base = os.path.expanduser(f"~/Desktop/code/{name}")
    os.makedirs(base, exist_ok=True)

    created = []
    for filepath, content in files.items():
        full_path = os.path.join(base, filepath)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            f.write(content)
        created.append(filepath)

    return {
        "id": request_id,
        "status": "ok",
        "message": f"Project '{name}' created at {base}",
        "path": base,
        "files_created": created,
    }


def run_claude_code(request_id: str, prompt: str, cwd: str = None) -> dict:
    """Run Claude Code CLI with a prompt. Uses the user's Max plan — no API credits."""
    cwd = os.path.expanduser(cwd) if cwd else os.path.expanduser("~/Desktop/code")

    try:
        result = subprocess.run(
            ["claude", "-p", "--output-format", "text", prompt],
            capture_output=True, text=True,
            timeout=300,  # 5 min timeout for coding tasks
            cwd=cwd,
        )
        output = result.stdout[-10000:] if result.stdout else ""
        error = result.stderr[-3000:] if result.stderr else ""

        return {
            "id": request_id,
            "status": "ok" if result.returncode == 0 else "error",
            "output": output,
            "stderr": error,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"id": request_id, "status": "error", "error": "Claude Code timed out (5 min)"}
    except FileNotFoundError:
        return {"id": request_id, "status": "error", "error": "Claude Code CLI not found. Install: npm install -g @anthropic-ai/claude-code"}
    except Exception as e:
        return {"id": request_id, "status": "error", "error": str(e)}


def get_system_info(request_id: str) -> dict:
    """Get system information."""
    cpu = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    battery = psutil.sensors_battery()

    info = {
        "cpu_percent": cpu,
        "memory_percent": mem.percent,
        "memory_total_gb": round(mem.total / (1024**3), 1),
        "disk_percent": disk.percent,
        "disk_total_gb": round(disk.total / (1024**3), 1),
        "platform": platform.platform(),
        "hostname": platform.node(),
    }

    if battery:
        info["battery_percent"] = battery.percent
        info["battery_plugged"] = battery.power_plugged

    return {"id": request_id, "status": "ok", "type": "system_info", "info": info}


async def main(server_url: str):
    """Connect to SAM server and handle commands."""
    ws_url = f"{server_url}/ws/agent?token={AGENT_TOKEN}"

    print("╔══════════════════════════════════════════════╗")
    print("║       J.A.R.V.I.S  DESKTOP  AGENT           ║")
    print("╚══════════════════════════════════════════════╝")
    print(f"\n  Connecting to: {server_url}")

    while True:
        try:
            async with websockets.connect(ws_url) as ws:
                print("  ✓ Connected to SAM server!")
                print("  MacBook is now accessible. Waiting for commands...\n")

                async for message in ws:
                    data = json.loads(message)
                    print(f"  → Command: {data.get('type', '?')}")

                    result = handle_command(data)
                    await ws.send(json.dumps(result))

                    status = result.get("status", "?")
                    print(f"  ← Result: {status}")

        except (websockets.ConnectionClosed, ConnectionRefusedError, OSError) as e:
            print(f"  ✗ Connection lost: {e}")
            print("  Reconnecting in 5 seconds...")
            await asyncio.sleep(5)


if __name__ == "__main__":
    server = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SERVER
    # Normalize URL
    if server.startswith("http://"):
        server = "ws://" + server[7:]
    elif server.startswith("https://"):
        server = "wss://" + server[8:]
    elif not server.startswith("ws"):
        server = "ws://" + server

    asyncio.run(main(server))
