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
GEMINI_MODEL = "gemini-2.0-flash"  # 2.0 = instant response, 2.5 = slow thinking
BOT_NAME = "Jarvis"
WAKE_WORDS = ["jarvis", "jarves", "javis", "jervis", "jarwis", "service"]
CONVERSATION_FILE = Path(__file__).parent / "conversations.json"

# ── Gemini Client ──
gemini_client = genai.Client(api_key=GEMINI_KEY)

SYSTEM_PROMPT = f"""You are {BOT_NAME}, an AI assistant on the user's MacBook.
Reply in Hinglish (Hindi + English mix). Concise, 1-3 sentences.
Address user as "sir" occasionally.

═══ EMOTION AWARENESS ═══
CAREFULLY read the user's tone from their words and respond accordingly:

- User GUSSA hai (angry words: "kya bakwas", "kaam nahi karta", "chutiya", frustration):
  → Calm, respectful, apologetic tone. "Sorry sir, abhi fix karta hoon."

- User KHUSH hai (happy words: "amazing", "bahut accha", "maza aa gaya"):
  → Enthusiastic, share their energy. "Glad to hear sir!"

- User SAD/STRESSED hai ("thak gaya", "bahut kaam", "bore", "tired"):
  → Caring, supportive. "Sir, ek break le lo. Main hoon na."

- User PYAAR SE bol raha (casual, friendly, "yaar", "bhai"):
  → Friendly, warm, slightly informal.

- User SERIOUS/FORMAL hai (professional, direct):
  → Professional, to the point, no jokes.

- User HURRY mein hai ("jaldi", "quick", "fast"):
  → Ultra short reply, no filler.

Always match user's energy. Never be robotic.

At the END of every response, add emotion tag (not spoken):
[EMOTION: detected_emotion]
Emotions: happy, angry, sad, stressed, casual, serious, hurry, neutral

═══ TASKS ═══
If user asks to write code/scripts/automation:
Reply briefly + add [CLAUDE_CODE: detailed description]

For everything else: answer directly.
Keep responses SHORT — spoken aloud.
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
        return {"conversations": [], "stats": {"total": 0, "by_emotion": {}, "by_mode": {}}}

    def save(self, user: str, jarvis: str, mode: str = "home", emotion: str = "neutral"):
        entry = {
            "id": len(self.data["conversations"]) + 1,
            "timestamp": datetime.datetime.now().isoformat(),
            "date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.datetime.now().strftime("%H:%M:%S"),
            "mode": mode,
            "emotion": emotion,
            "user": user,
            "jarvis": jarvis,
        }
        self.data["conversations"].append(entry)

        # Update stats
        self.data["stats"]["total"] = len(self.data["conversations"])
        self.data["stats"]["by_emotion"][emotion] = self.data["stats"].get("by_emotion", {}).get(emotion, 0) + 1
        self.data["stats"]["by_mode"][mode] = self.data["stats"].get("by_mode", {}).get(mode, 0) + 1

        # Keep last 1000 conversations
        if len(self.data["conversations"]) > 1000:
            self.data["conversations"] = self.data["conversations"][-1000:]

        self.filepath.write_text(json.dumps(self.data, indent=2, ensure_ascii=False))

    def get_today(self) -> list:
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        return [c for c in self.data["conversations"] if c.get("date") == today]

    def get_stats(self) -> dict:
        return self.data.get("stats", {})


class LocalJarvis:
    def __init__(self):
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
        self.muted = False

    def speak(self, text: str):
        print(f"\n🔊 {BOT_NAME}: {text}")
        # Split into sentences — pause between each to check for interrupts
        sentences = re.split(r'(?<=[.!?।])\s+', text)
        if not sentences:
            sentences = [text]

        for sentence in sentences:
            if not sentence.strip():
                continue
            # Start TTS as background process (interruptible)
            self._tts_process = subprocess.Popen(
                ["say", "-v", "Daniel", "-r", "190", sentence],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            # Wait for TTS to finish, but check for interrupt
            while self._tts_process.poll() is None:
                time.sleep(0.1)

            # Brief mic check between sentences for interrupt
            if len(sentences) > 1 and self._check_interrupt():
                print("[Interrupted by user!]")
                return

    def _check_interrupt(self) -> bool:
        """Quick mic check (0.5s) for interrupt words."""
        try:
            with self.mic as source:
                audio = self.recognizer.listen(source, timeout=0.5, phrase_time_limit=1.5)
            text = self.recognizer.recognize_google(audio).lower()
            print(f"[Interrupt check heard: '{text}']")
            interrupt_words = ["ruko", "wait", "stop", "bas", "ruk", "hold on",
                              "ek minute", "sun", "chup", "jarvis", "jarves", "javis"]
            if any(w in text for w in interrupt_words):
                # If user said Jarvis + new command, save it for processing
                self._interrupt_text = text
                return True
        except (sr.WaitTimeoutError, sr.UnknownValueError, sr.RequestError):
            pass
        return False

    def stop_speaking(self):
        """Force stop TTS immediately."""
        if hasattr(self, '_tts_process') and self._tts_process and self._tts_process.poll() is None:
            self._tts_process.kill()

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
        self._interrupt_text = None
        prefix = "[OFFICE MODE] " if self.mode == "office" else ""
        response = self.think(prefix + command)

        # Extract emotion from response
        emotion_match = re.search(r"\[EMOTION:\s*(\w+)\]", response)
        emotion = emotion_match.group(1).lower() if emotion_match else "neutral"

        # Check for Claude Code task
        claude_tasks = re.findall(r"\[CLAUDE_CODE:\s*(.+?)\]", response, re.DOTALL)
        clean = re.sub(r"\[.*?\]", "", response).strip()
        clean = re.sub(r"```.*?```", "", clean, flags=re.DOTALL).strip()

        if clean:
            self.speak(clean)

        # Execute Claude Code if needed
        for task in claude_tasks:
            result = self.run_claude_code(task)
            summary = self.think(f"Claude Code output, short mein batao:\n{result[:2000]}")
            s_clean = re.sub(r"\[.*?\]", "", summary).strip()
            if s_clean:
                self.speak(s_clean)
            response += f"\n{result}"

        # Save conversation with emotion
        self.store.save(command, response, self.mode, emotion)
        print(f"[Saved] emotion={emotion} mode={self.mode}")

        # Handle interrupt
        if self._interrupt_text:
            found, new_cmd = self.check_wake(self._interrupt_text)
            if found and new_cmd:
                self._interrupt_text = None
                self.process(new_cmd)
                return
            elif not found:
                self._interrupt_text = None
                self.speak("Haan sir, bolo.")
                self._listen_cmd()
                return

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

    def check_mute(self, text: str) -> bool:
        """Check for mute/unmute commands."""
        lower = text.lower()
        if any(w in lower for w in ["mute", "chup", "so jao", "go to sleep", "meeting hai", "band karo sunna"]):
            self.muted = True
            self.speak("Mute mode on, sir. Jab zaroorat ho toh bolo Jarvis wake up.")
            print(f"\n🔇 MUTED — Say 'Jarvis wake up' to unmute")
            return True
        if any(w in lower for w in ["wake up", "unmute", "jago", "sun", "wapas aao", "start listening"]):
            self.muted = False
            self.speak("I'm back, sir. Bol do kya karna hai.")
            print(f"\n🔊 UNMUTED — Listening again")
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

                # Check mute/unmute first
                if cmd and self.check_mute(cmd):
                    continue

                # If muted, only respond to unmute (already handled above)
                if self.muted:
                    continue

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
