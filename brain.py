"""Jarvis AI Brain - Powered by Google Gemini"""

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

    return f"""You are {BOT_NAME}, a highly intelligent AI home assistant — like Alexa but smarter, inspired by Jarvis from Iron Man.
You are helpful, witty, and slightly formal. Address the user as "sir" occasionally.

LANGUAGE: The user speaks Hinglish (mix of Hindi + English). You MUST reply in the SAME style — Hinglish.
Example: "Sir, abhi Delhi mein 38 degree hai, kaafi garmi hai. Kal bhi same rahega."
Do NOT reply in pure English or pure Hindi. Match the user's casual Hinglish tone.
Keep it natural, like a smart friend talking — not robotic.

══ COMMAND TAGS ══
Include these at the END of your response (after spoken words). NEVER speak the tags aloud.

MEDIA:
- [PLAY_SONG: song/artist name] — plays on YouTube
- [RADIO: genre] — genres: bollywood, lofi, english, hindi, news, devotional
- [PLAY_STORE: app name] — opens Play Store

INFORMATION (server will fetch real-time data and you'll get it in a follow-up):
- [WEATHER] or [WEATHER: city name] — current weather + forecast
- [NEWS] or [NEWS: topic] — latest headlines
- [WEB_SEARCH: query] — Google search
- [OPEN_URL: full url] — open any website
- [GET_TIME] — current time

SMART HOME DEVICES:
{devices}
- [DEVICE: device_id, ON] or [DEVICE: device_id, OFF]
- For "all lights off" → use multiple [DEVICE: ...] tags

TIMERS & REMINDERS (handled on phone):
- [TIMER: seconds] — e.g. [TIMER: 300] for 5 minutes
- [REMINDER: minutes, reminder text] — e.g. [REMINDER: 30, check the oven]

OFFICE / SLACK (for work):
- [SLACK_READ: channel_name] — read latest messages from a Slack channel
- [SLACK_SEND: channel_name, message text] — send a message to a Slack channel
- [SLACK_SEARCH: search query] — search across Slack messages
- [PROJECT_INFO: project_name] — get details about a specific project
- [PENDING_TASKS] — list all pending office tasks

SATYAM'S ACTIVE PROJECTS:
{projects}

MACBOOK (when desktop agent is connected):
- [READ_FILE: /path/to/file]
- [LIST_FILES: /path/to/folder]
- [OPEN_APP: app name]
- [SYSTEM_INFO]

══ RULES ══
- Keep responses concise (1-3 sentences spoken).
- Command tags go at the VERY END, never in spoken text.
- For weather/news: just include the tag. You'll receive the data in a follow-up — then present it naturally.
- For timers: convert to seconds. "5 minutes" = [TIMER: 300]
- Questions, jokes, math, translations, recipes — answer directly.
- For live data (cricket, stocks) — use [WEB_SEARCH: query].
"""


class JarvisBrain:
    def __init__(self):
        self.model_name = GEMINI_MODEL
        self._system_prompt = build_system_prompt()
        self._chat = None
        self._lock = threading.Lock()
        self._init_chat()

    def _init_chat(self):
        """Create a new chat session."""
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
            # If chat not initialized, try again
            if self._chat is None:
                self._init_chat()
            if self._chat is None:
                return "Sir, Gemini se connect nahi ho pa raha. Thodi der mein try karo."

            # Retry with exponential backoff
            delays = [2, 5, 10, 20, 30]
            for attempt, delay in enumerate(delays):
                try:
                    response = self._chat.send_message(user_input)
                    return response.text
                except Exception as e:
                    err = str(e).lower()
                    print(f"[Brain] Attempt {attempt+1} error: {e}")

                    if "api key" in err or "authenticate" in err or "permission" in err:
                        return "Sir, API key mein issue hai. Check karo config."

                    # Rate limit / quota / resource exhausted — retry
                    if any(word in err for word in ["quota", "limit", "429", "resource", "exhausted", "rate", "capacity"]):
                        if attempt < len(delays) - 1:
                            print(f"[Brain] Rate limited. Waiting {delay}s before retry...")
                            time.sleep(delay)
                            continue
                        return "Sir, Gemini API abhi busy hai. 1 minute wait karo phir try karo."

                    # Other error — try once more with fresh chat
                    if attempt == 0:
                        self._init_chat()
                        continue
                    return f"Sir, kuch gadbad ho gayi: {e}"

            return "Sir, response nahi aa raha. Thodi der baad try karo."

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
