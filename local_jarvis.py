"""
╔══════════════════════════════════════════════╗
║     J.A.R.V.I.S  LOCAL VOICE ASSISTANT       ║
║  Gemini (voice) + Claude Code CLI (coding)   ║
╚══════════════════════════════════════════════╝

Usage:  python local_jarvis.py
"""

import os
import re
import json
import time
import datetime
import subprocess
import speech_recognition as sr
import pyttsx3
from google import genai
from pathlib import Path

# ── Load .env ──
_env = Path(__file__).parent / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

# ── Config ──
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"
BOT_NAME = "Jarvis"
WAKE_WORDS = ["jarvis", "jarves", "javis", "jervis", "hello", "hey"]
CONVERSATION_FILE = Path(__file__).parent / "conversations.json"

# ── Gemini Client ──
gemini_client = genai.Client(api_key=GEMINI_KEY)

SYSTEM_PROMPT = f"""You are {BOT_NAME}, an AI assistant on the user's MacBook.
Reply in Hinglish (Hindi + English mix). Concise, 1-3 sentences.
Address user as "sir" occasionally. Be witty and natural.

If user asks to write code, create scripts, build automation, or any coding task:
Reply briefly like "Sir, Claude se code likhwa raha hoon" and add [CLAUDE_CODE: detailed description]

For everything else (questions, jokes, math, info): answer directly.
Keep responses SHORT — they'll be spoken aloud.
"""


class ConversationStore:
    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.data = self._load()

    def _load(self) -> dict:
        if self.filepath.exists():
            try:
                return json.loads(self.filepath.read_text())
            except (json.JSONDecodeError, IOError):
                pass
        return {"conversations": []}

    def save(self, user: str, jarvis: str, mode: str = "home"):
        self.data["conversations"].append({
            "timestamp": datetime.datetime.now().isoformat(),
            "mode": mode,
            "user": user,
            "jarvis": jarvis,
        })
        if len(self.data["conversations"]) > 500:
            self.data["conversations"] = self.data["conversations"][-500:]
        self.filepath.write_text(json.dumps(self.data, indent=2, ensure_ascii=False))


class LocalJarvis:
    def __init__(self):
        # TTS
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", 175)
        self.engine.setProperty("volume", 1.0)
        for v in self.engine.getProperty("voices"):
            if "daniel" in v.name.lower() or "male" in v.name.lower():
                self.engine.setProperty("voice", v.id)
                break

        # STT
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.mic = sr.Microphone()

        # Chat
        self.chat = gemini_client.chats.create(
            model=GEMINI_MODEL,
            config={"system_instruction": SYSTEM_PROMPT},
        )
        self.store = ConversationStore(CONVERSATION_FILE)
        self.mode = "home"

    def speak(self, text: str):
        print(f"\n🔊 {BOT_NAME}: {text}")
        self.engine.say(text)
        self.engine.runAndWait()

    def listen(self, timeout=None, phrase_limit=15) -> str | None:
        with self.mic as source:
            try:
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
            except sr.WaitTimeoutError:
                return None
        try:
            text = self.recognizer.recognize_google(audio)
            print(f"\n🎤 You: {text}")
            return text
        except (sr.UnknownValueError, sr.RequestError):
            return None

    def think(self, text: str) -> str:
        """Ask Gemini Flash for quick response."""
        try:
            r = self.chat.send_message(text)
            return r.text
        except Exception as e:
            return f"Sir, error: {e}"

    def run_claude_code(self, prompt: str) -> str:
        """Run Claude Code CLI for coding tasks. Uses Max plan — free!"""
        print(f"\n⚡ Running Claude Code CLI...")
        self.speak("Sir, Claude se kaam karwa raha hoon. Thoda wait karo.")
        try:
            result = subprocess.run(
                ["claude", "-p", "--output-format", "text", prompt],
                capture_output=True, text=True, timeout=300,
                cwd=os.path.expanduser("~/Desktop/code"),
            )
            if result.returncode == 0 and result.stdout:
                output = result.stdout[-3000:]
                return f"Claude ne yeh kiya:\n{output}"
            else:
                return f"Error: {result.stderr[-500:]}" if result.stderr else "Claude se response nahi aaya."
        except subprocess.TimeoutExpired:
            return "Claude Code timeout ho gaya (5 min)."
        except FileNotFoundError:
            return "Claude Code CLI nahi mila. Install karo: npm install -g @anthropic-ai/claude-code"
        except Exception as e:
            return f"Error: {e}"

    def process(self, command: str):
        prefix = "[OFFICE MODE] " if self.mode == "office" else ""
        response = self.think(prefix + command)

        # Check for Claude Code task
        claude_tasks = re.findall(r"\[CLAUDE_CODE:\s*(.+?)\]", response, re.DOTALL)
        clean = re.sub(r"\[.*?\]", "", response).strip()
        clean = re.sub(r"```.*?```", "", clean, flags=re.DOTALL).strip()

        if clean:
            self.speak(clean)

        # Execute Claude Code if needed
        for task in claude_tasks:
            result = self.run_claude_code(task)
            # Summarize result via Gemini
            summary = self.think(f"Claude Code ne yeh output diya, user ko short mein batao:\n{result[:2000]}")
            summary_clean = re.sub(r"\[.*?\]", "", summary).strip()
            if summary_clean:
                self.speak(summary_clean)
            response += f"\n{result}"

        self.store.save(command, response, self.mode)

    def check_wake(self, text: str) -> tuple[bool, str]:
        lower = text.lower()
        for w in WAKE_WORDS:
            pos = lower.find(w)
            if pos != -1:
                after = text[pos + len(w):].strip()
                after = re.sub(r"^[,.\s]*(hey|hello|hi|okay|ok|please|jarvis)?\s*", "", after, flags=re.I).strip()
                return True, after
        return False, ""

    def check_mode(self, text: str) -> bool:
        lower = text.lower()
        if any(w in lower for w in ["office mode", "switch to office", "office karo"]):
            self.mode = "office"
            self.speak("Office mode on, sir.")
            return True
        if any(w in lower for w in ["home mode", "switch to home", "normal mode"]):
            self.mode = "home"
            self.speak("Home mode, sir.")
            return True
        return False

    def run(self):
        if not GEMINI_KEY:
            print("❌ GEMINI_API_KEY not set! Add it to .env")
            return

        print(f"\n[{BOT_NAME}] Calibrating mic...")
        with self.mic as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=2)

        self.speak(f"{BOT_NAME} online, sir. Bolo kya karna hai.")
        print(f"\n{'='*50}")
        print(f"  {BOT_NAME} LISTENING")
        print(f"  Say 'Hey Jarvis' or 'Hello'")
        print(f"  Gemini Flash (voice) + Claude Code CLI (coding)")
        print(f"  Ctrl+C to quit")
        print(f"{'='*50}\n")

        while True:
            try:
                text = self.listen(timeout=None)
                if not text:
                    continue

                found, cmd = self.check_wake(text)
                if not found:
                    continue

                print("[Wake word detected!]")

                if cmd and self.check_mode(cmd):
                    self._converse()
                    continue

                if cmd:
                    self.process(cmd)
                    self._converse()
                else:
                    self.speak("Yes sir?")
                    self._listen_cmd()

            except KeyboardInterrupt:
                self.speak("Goodbye, sir.")
                break
            except Exception as e:
                print(f"[Error] {e}")
                time.sleep(1)

    def _listen_cmd(self):
        text = self.listen(timeout=5)
        if not text:
            return
        if self.check_mode(text):
            self._converse()
            return
        self.process(text)
        self._converse()

    def _converse(self):
        while True:
            text = self.listen(timeout=10)
            if not text:
                print("[Silence — standby]")
                return
            lower = text.lower()
            if any(w in lower for w in ["thank", "thanks", "bye", "bas", "stop"]):
                self.speak("Alright sir.")
                return
            if self.check_mode(text):
                continue
            found, cmd = self.check_wake(text)
            if found and cmd:
                text = cmd
            self.process(text)


if __name__ == "__main__":
    LocalJarvis().run()
