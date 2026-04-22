"""SAM Smart Home Controller - Tuya/SmartLife device control"""

import json
import os
from config import TUYA_ACCESS_ID, TUYA_ACCESS_SECRET, TUYA_REGION

DEVICES_FILE = os.path.join(os.path.dirname(__file__), "devices.json")


def load_devices() -> list[dict]:
    """Load device list from devices.json."""
    try:
        with open(DEVICES_FILE, "r") as f:
            data = json.load(f)
        return data.get("devices", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def get_device_by_id(device_id: str) -> dict | None:
    """Find a device by its ID."""
    for d in load_devices():
        if d["id"] == device_id:
            return d
    return None


def find_device(query: str) -> dict | None:
    """Fuzzy find a device by name, room, or type.
    E.g. 'bedroom light', 'hall fan', 'light 1'
    """
    query_lower = query.lower()
    devices = load_devices()

    # Try exact ID match first
    for d in devices:
        if d["id"] == query_lower:
            return d

    # Try matching by room + type combination
    for d in devices:
        name = d.get("name", "").lower()
        room = d.get("room", "").lower()
        dtype = d.get("type", "").lower()

        if room in query_lower and dtype in query_lower:
            return d
        if name in query_lower or query_lower in name:
            return d

    # Try matching by just type (returns first match)
    for d in devices:
        dtype = d.get("type", "").lower()
        if dtype in query_lower:
            return d

    return None


def get_devices_summary() -> str:
    """Get a summary of all devices for the system prompt."""
    devices = load_devices()
    if not devices:
        return "No smart home devices configured."

    lines = []
    for d in devices:
        lines.append(f"  - {d['name']} (id: {d['id']}, room: {d.get('room', '?')}, type: {d.get('type', '?')})")
    return "\n".join(lines)


def control_device(device_id: str, action: str) -> dict:
    """Control a device: turn on/off.
    Returns result dict with status and message.
    """
    device = get_device_by_id(device_id)
    if not device:
        return {"status": "error", "message": f"Device '{device_id}' not found"}

    tuya_id = device.get("tuya_id")

    if not tuya_id:
        return {
            "status": "error",
            "message": f"Device '{device['name']}' is not configured yet. Add its tuya_id in devices.json"
        }

    if not TUYA_ACCESS_ID or not TUYA_ACCESS_SECRET:
        return {
            "status": "error",
            "message": "Tuya credentials not set. Add TUYA_ACCESS_ID and TUYA_ACCESS_SECRET in config.py"
        }

    # Control via Tuya Cloud API
    return _tuya_control(tuya_id, device["name"], action)


def _tuya_control(tuya_id: str, name: str, action: str) -> dict:
    """Control a Tuya device via Cloud API."""
    try:
        from tuya_connector import TuyaOpenAPI

        api = TuyaOpenAPI(
            f"https://openapi.tuya{_region_domain()}.com",
            TUYA_ACCESS_ID,
            TUYA_ACCESS_SECRET,
        )
        api.connect()

        # Standard Tuya switch command
        value = action.lower() in ("on", "true", "1")
        commands = {"commands": [{"code": "switch_1", "value": value}]}

        response = api.post(f"/v1.0/devices/{tuya_id}/commands", commands)

        if response.get("success"):
            state = "on" if value else "off"
            return {"status": "ok", "message": f"{name} turned {state}"}
        else:
            return {"status": "error", "message": f"Tuya error: {response.get('msg', 'unknown')}"}

    except ImportError:
        return {
            "status": "error",
            "message": "tuya-connector not installed. Run: pip install tuya-connector-python"
        }
    except Exception as e:
        return {"status": "error", "message": f"Error controlling {name}: {e}"}


def _region_domain() -> str:
    """Get Tuya API domain suffix for region."""
    regions = {"cn": "", "us": "", "eu": "eu", "in": "in"}
    return regions.get(TUYA_REGION, "")


def list_devices_formatted() -> str:
    """Get a formatted list of all devices."""
    devices = load_devices()
    if not devices:
        return "No devices configured."

    lines = []
    for d in devices:
        configured = "ready" if d.get("tuya_id") else "not configured"
        lines.append(f"  {d['name']} ({d['room']}) - {configured}")

    return "\n".join(lines)
