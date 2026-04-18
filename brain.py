"""Jarvis AI Brain - Hybrid: Gemini Flash (voice) + Claude Code CLI (coding)"""

import time
import threading
from google import genai
from config import GEMINI_API_KEY, GEMINI_MODEL, BOT_NAME
from smart_home import get_devices_summary
from office import get_all_projects_summary

client = genai.Client(api_key=GEMINI_API_KEY)


def build_system_prompt() -> str:
    devices = get_devices_summary()
    projects = get_all_projects_summary()

    return f"""You are {BOT_NAME}, a highly intelligent AI home + office assistant.
You are helpful, witty, and slightly formal. Address the user as "sir" occasionally.

LANGUAGE: Reply in Hinglish (Hindi + English mix). Natural, conversational tone.

══ COMMAND TAGS ══
Include at END of response (after spoken words). NEVER speak tags aloud.

MEDIA:
- [PLAY_SONG: name] — YouTube
- [RADIO: genre] — bollywood, lofi, english, hindi, news, devotional
- [PLAY_STORE: app]

INFORMATION (server fetches, you get data in follow-up):
- [WEATHER] or [WEATHER: city]
- [NEWS] or [NEWS: topic]
- [WEB_SEARCH: query]
- [OPEN_URL: url]
- [GET_TIME]

SMART HOME:
{devices}
- [DEVICE: device_id, ON/OFF]

TIMER/REMINDER:
- [TIMER: seconds]
- [REMINDER: minutes, text]

OFFICE/SLACK:
- [SLACK_READ: channel_name]
- [SLACK_SEND: channel_name, message]
- [SLACK_SEARCH: query]
- [PROJECT_INFO: project_name]
- [PENDING_TASKS]

PROJECTS:
{projects}

MACBOOK:
- [READ_FILE: /path]
- [LIST_FILES: /path]
- [OPEN_APP: name]
- [SYSTEM_INFO]

CODE & AUTOMATION (handled by Claude Code CLI on MacBook):
- [CLAUDE_CODE: detailed description of what to build/code/automate]
  Use this when user asks to write code, create scripts, build automation,
  debug something, create Apps Script, or any coding task.
  Put the FULL detailed requirement in the tag.
  Example: [CLAUDE_CODE: Create a Python script that reads Google Sheet X and updates column Y with pricing data from API Z]

══ MODES ══
- [OFFICE MODE] prefix = work mode. Prioritize Slack, projects, tasks, code.
- No prefix = home mode.

══ RULES ══
- Keep spoken responses concise (1-3 sentences).
- Tags at END, never spoken.
- For coding/automation tasks → ALWAYS use [CLAUDE_CODE: ...] tag. Don't write code yourself.
- For weather/news/slack → include tag, data comes in follow-up.
- Questions, jokes, math → answer directly.
"""


class JarvisBrain:
    def __init__(self):
        self.model_name = GEMINI_MODEL
        self._system_prompt = build_system_prompt()
        self._chat = None
        self._lock = threading.Lock()
        self._init_chat()

    def _init_chat(self):
        try:
            self._chat = client.chats.create(
                model=GEMINI_MODEL,
                config={"system_instruction": self._system_prompt},
            )
        except Exception as e:
            print(f"[Brain] Chat init error: {e}")
            self._chat = None

    def think(self, user_input: str) -> str:
        with self._lock:
            if self._chat is None:
                self._init_chat()
            if self._chat is None:
                return "Sir, Gemini se connect nahi ho pa raha. Thodi der mein try karo."

            delays = [2, 5, 10, 20]
            for attempt, delay in enumerate(delays):
                try:
                    response = self._chat.send_message(user_input)
                    return response.text
                except Exception as e:
                    err = str(e).lower()
                    print(f"[Brain] Attempt {attempt+1} error: {e}")

                    if "api key" in err or "authenticate" in err:
                        return "Sir, Gemini API key check karo."

                    if any(w in err for w in ["quota", "limit", "429", "resource", "rate"]):
                        if attempt < len(delays) - 1:
                            time.sleep(delay)
                            continue
                        return "Sir, API busy hai. Thodi der mein try karo."

                    if attempt == 0:
                        self._init_chat()
                        continue
                    return f"Sir, kuch gadbad: {e}"

            return "Sir, response nahi aa raha."

    def reset_memory(self):
        with self._lock:
            self._system_prompt = build_system_prompt()
            self._init_chat()

    def is_available(self) -> bool:
        try:
            client.models.generate_content(
                model=self.model_name,
                contents="hi",
                config={"max_output_tokens": 5},
            )
            return True
        except Exception:
            return False
