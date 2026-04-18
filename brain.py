"""Jarvis AI Brain - Powered by Claude (Anthropic)"""

import time
import threading
import anthropic
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, BOT_NAME
from smart_home import get_devices_summary
from office import get_all_projects_summary

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


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
- For weather/news/slack: just include the tag. You'll receive the data in a follow-up — then present it naturally.
- For timers: convert to seconds. "5 minutes" = [TIMER: 300]
- Questions, jokes, math, translations, recipes — answer directly.
- For live data (cricket, stocks) — use [WEB_SEARCH: query].
"""


class JarvisBrain:
    def __init__(self):
        self.model_name = CLAUDE_MODEL
        self._system_prompt = build_system_prompt()
        self._messages = []  # Conversation history
        self._lock = threading.Lock()

    def think(self, user_input: str) -> str:
        with self._lock:
            self._messages.append({"role": "user", "content": user_input})

            # Keep last 40 messages to stay within context
            if len(self._messages) > 40:
                self._messages = self._messages[-40:]

            delays = [2, 5, 10, 20]
            for attempt, delay in enumerate(delays):
                try:
                    response = client.messages.create(
                        model=self.model_name,
                        max_tokens=1024,
                        system=self._system_prompt,
                        messages=self._messages,
                    )
                    reply = response.content[0].text
                    self._messages.append({"role": "assistant", "content": reply})
                    return reply

                except anthropic.RateLimitError:
                    if attempt < len(delays) - 1:
                        time.sleep(delay)
                        continue
                    return "Sir, API abhi busy hai. Thodi der mein try karo."

                except anthropic.AuthenticationError:
                    return "Sir, API key mein issue hai. ANTHROPIC_API_KEY check karo."

                except Exception as e:
                    if attempt < 1:
                        time.sleep(2)
                        continue
                    return f"Sir, kuch gadbad ho gayi: {e}"

            return "Sir, response nahi aa raha. Thodi der baad try karo."

    def reset_memory(self):
        with self._lock:
            self._system_prompt = build_system_prompt()
            self._messages = []

    def is_available(self) -> bool:
        try:
            client.messages.create(
                model=self.model_name,
                max_tokens=5,
                messages=[{"role": "user", "content": "hi"}],
            )
            return True
        except Exception:
            return False
