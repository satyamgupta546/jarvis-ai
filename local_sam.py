"""
╔══════════════════════════════════════════════╗
║     S.A.M  LOCAL VOICE ASSISTANT       ║
║  Whisper (STT) + Groq (fast) + Claude (code) ║
╚══════════════════════════════════════════════╝

Usage:  python local_sam.py
"""

import os
import re
import json
import time
import datetime
import subprocess
import tempfile
import struct
import threading
import speech_recognition as sr
from groq import Groq
from pathlib import Path

# ── Audio Boost ──
AUDIO_GAIN = 8  # Multiply audio volume by this (1 = no change, 5-10 = good for weak mics)

def boost_audio(raw_data: bytes, gain: int = AUDIO_GAIN) -> bytes:
    """Amplify raw audio samples to fix low mic volume."""
    samples = struct.unpack(f'{len(raw_data)//2}h', raw_data)
    boosted = []
    for s in samples:
        s = int(s * gain)
        s = max(-32768, min(32767, s))  # Clamp to 16-bit range
        boosted.append(s)
    return struct.pack(f'{len(boosted)}h', *boosted)

# ── Load .env ──
_env = Path(__file__).parent / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

# ── Config ──
BOT_NAME = "SAM"
GROQ_KEY = os.environ.get("GROQ_API_KEY", "")
CLAUDE_CLI = "claude"
WAKE_WORDS = ["sam", "sonik", "sam", "hey sam"]
CONVERSATION_FILE = Path(__file__).parent / "conversations.json"

# ── Groq Client ──
groq_client = Groq(api_key=GROQ_KEY)

SYSTEM_PROMPT = f"""You are {BOT_NAME}, an AI assistant on the user's MacBook.
Reply in Hinglish (Hindi + English mix). Concise, 1-3 sentences.
Address user as "sir" occasionally.

═══ EMOTION AWARENESS ═══
Read the user's tone and respond accordingly:
- Angry → Calm, respectful. "Sorry sir, abhi fix karta hoon."
- Happy → Enthusiastic. "Glad to hear sir!"
- Sad/Stressed → Caring. "Sir, ek break le lo."
- Casual → Friendly, warm.
- Serious → Professional, direct.
- Hurry → Ultra short reply.

At END of every response, add (not spoken): [EMOTION: detected_emotion]
Emotions: happy, angry, sad, stressed, casual, serious, hurry, neutral

═══ TASKS ═══
If user asks to write code, create scripts, build automation:
Reply briefly + add [CLAUDE_CODE: detailed description]

For everything else: answer directly. Keep SHORT — spoken aloud.
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

    def save(self, user: str, sam: str, mode: str = "home", emotion: str = "neutral"):
        entry = {
            "id": len(self.data["conversations"]) + 1,
            "timestamp": datetime.datetime.now().isoformat(),
            "date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.datetime.now().strftime("%H:%M:%S"),
            "mode": mode,
            "emotion": emotion,
            "user": user,
            "sam": sam,
        }
        self.data["conversations"].append(entry)
        self.data["stats"]["total"] = len(self.data["conversations"])
        em = self.data["stats"].setdefault("by_emotion", {})
        em[emotion] = em.get(emotion, 0) + 1
        mo = self.data["stats"].setdefault("by_mode", {})
        mo[mode] = mo.get(mode, 0) + 1

        if len(self.data["conversations"]) > 1000:
            self.data["conversations"] = self.data["conversations"][-1000:]
        self.filepath.write_text(json.dumps(self.data, indent=2, ensure_ascii=False))


class LocalSAM:
    def __init__(self):
        # Whisper STT
        # Mic
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 100  # Low threshold for weak MacBook mic
        self.recognizer.dynamic_energy_threshold = False  # Fixed, no auto-adjust
        self.mic = sr.Microphone()

        # Chat history for Groq
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.store = ConversationStore(CONVERSATION_FILE)
        self.mode = "home"
        self.muted = False
        self._interrupt_text = None
        self._tts_process = None

    def speak(self, text: str):
        """Speak via macOS say — interruptible."""
        print(f"\n🔊 {BOT_NAME}: {text}")
        sentences = re.split(r'(?<=[.!?।])\s+', text)
        if not sentences:
            sentences = [text]

        for sentence in sentences:
            if not sentence.strip():
                continue
            self._tts_process = subprocess.Popen(
                ["say", "-v", "Daniel", "-r", "190", sentence],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            while self._tts_process.poll() is None:
                time.sleep(0.1)

    def listen(self, timeout=None, phrase_limit=15) -> str | None:
        """Listen via mic → boost volume → transcribe with Groq Whisper."""
        with self.mic as source:
            try:
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
            except sr.WaitTimeoutError:
                return None

        try:
            # Boost audio volume (fix for weak MacBook mic)
            raw = audio.get_raw_data()
            boosted_raw = boost_audio(raw)

            # Create boosted AudioData
            boosted_audio = sr.AudioData(boosted_raw, audio.sample_rate, audio.sample_width)

            # Save boosted audio to temp WAV
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(boosted_audio.get_wav_data())
                temp_path = f.name

            # Transcribe with Groq Whisper API (cloud, fast, accurate)
            with open(temp_path, 'rb') as f:
                result = groq_client.audio.transcriptions.create(
                    file=(temp_path, f.read()),
                    model="whisper-large-v3",
                    language="en",
                    response_format="text",
                )

            os.unlink(temp_path)
            text = result.strip() if result else None

            if text:
                print(f"\n🎤 You: {text}")
            return text if text else None

        except Exception as e:
            print(f"[STT error] {e}")
            return None

    def think(self, text: str) -> str:
        """Ask Groq — instant response (<0.1s)."""
        self.messages.append({"role": "user", "content": text})

        # Keep last 20 messages + system
        if len(self.messages) > 21:
            self.messages = [self.messages[0]] + self.messages[-20:]

        try:
            r = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=self.messages,
                max_tokens=256,
                temperature=0.7,
            )
            reply = r.choices[0].message.content
            self.messages.append({"role": "assistant", "content": reply})
            return reply
        except Exception as e:
            return f"Sir, error: {e}"

    def run_claude_code(self, prompt: str) -> str:
        """Run Claude Code CLI for coding tasks."""
        print(f"\n⚡ Running Claude Code CLI...")
        self.speak("Sir, Claude se kaam karwa raha hoon. Thoda wait karo.")
        try:
            result = subprocess.run(
                [CLAUDE_CLI, "-p", "--output-format", "text"],
                input=prompt, capture_output=True, text=True, timeout=300,
                cwd=os.path.expanduser("~/Desktop/code"),
            )
            if result.returncode == 0 and result.stdout:
                return result.stdout[-3000:]
            return f"Error: {result.stderr[-500:]}" if result.stderr else "Claude se response nahi aaya."
        except subprocess.TimeoutExpired:
            return "Claude Code timeout (5 min)."
        except Exception as e:
            return f"Error: {e}"

    def process(self, command: str):
        """Process command: Groq for chat, Claude for code."""
        self._interrupt_text = None
        prefix = "[OFFICE MODE] " if self.mode == "office" else ""
        response = self.think(prefix + command)

        # Extract emotion
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
            summary = self.think(f"Claude Code output, user ko short mein batao:\n{result[:2000]}")
            s_clean = re.sub(r"\[.*?\]", "", summary).strip()
            if s_clean:
                self.speak(s_clean)
            response += f"\n{result}"

        # Save conversation
        self.store.save(command, response, self.mode, emotion)
        print(f"[Saved] emotion={emotion} mode={self.mode}")

    def check_wake(self, text: str) -> tuple[bool, str]:
        lower = text.lower()
        for w in WAKE_WORDS:
            pos = lower.find(w)
            if pos != -1:
                after = text[pos + len(w):].strip()
                after = re.sub(r"^[,.\s]*(hey|hello|hi|okay|ok|please|sam)?\s*", "", after, flags=re.I).strip()
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
        lower = text.lower()
        if any(w in lower for w in ["mute", "chup", "so jao", "go to sleep", "meeting hai"]):
            self.muted = True
            self.speak("Mute mode on, sir. SAM wake up bolna jab zaroorat ho.")
            print(f"\n🔇 MUTED")
            return True
        if any(w in lower for w in ["wake up", "unmute", "jago", "sun", "wapas aao"]):
            self.muted = False
            self.speak("I'm back, sir.")
            print(f"\n🔊 UNMUTED")
            return True
        return False

    def run(self):
        if not GROQ_KEY:
            print("❌ GROQ_API_KEY not set! Add it to .env")
            return

        print(f"\n[{BOT_NAME}] Calibrating mic...")
        with self.mic as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=2)

        self.speak(f"{BOT_NAME} online, sir. Whisper listening, Groq brain ready.")
        print(f"\n{'='*50}")
        print(f"  {BOT_NAME} LISTENING")
        print(f"  STT: Whisper (accurate)")
        print(f"  Chat: Groq (instant)")
        print(f"  Code: Claude CLI (your Max plan)")
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

                if cmd and self.check_mute(cmd):
                    continue
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
        if self.check_mute(text):
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
            if self.check_mute(text):
                return
            if self.check_mode(text):
                continue
            found, cmd = self.check_wake(text)
            if found and cmd:
                text = cmd
            self.process(text)


if __name__ == "__main__":
    LocalSAM().run()
