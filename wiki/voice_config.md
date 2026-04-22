# Voice Configuration

## Overview
SAM ki voice, wake word detection, mute, aur interrupt settings.

---

## Wake Words
SAM tab activate hota hai jab yeh words sune:
- `sam`, `jarves`, `javis`, `jervis`, `jarwis`, `service`

**Note:** "hello" aur "hey" hata diye hain — meeting mein false trigger hota tha.

## Interrupt Words
SAM bol raha ho toh beech mein rokne ke liye:
- `ruko`, `ruk`, `bas`, `stop`, `wait`, `hold on`, `ek minute`, `sun`, `chup`
- `sam` (beech mein bolo toh ruk ke naya command sunega)

**How it works:** TTS sentences mein split hota hai, har sentence ke beech mic check hota hai.

## Mute Mode (Meeting ke liye)
| Activate | Phrases |
|----------|---------|
| Mute | "SAM mute", "SAM chup", "SAM so jao", "SAM meeting hai" |
| Unmute | "SAM wake up", "SAM jago", "SAM unmute", "SAM sun" |

Mute mein: sirf unmute command pe respond karta hai, baaki sab ignore.

## TTS Voice (MacBook Local)
- **Engine:** macOS native `say` command
- **Voice:** Daniel (British male — SAM-like)
- **Speed:** 190 WPM
- **Alternative:** Aman (Indian English)

Change voice in `local_sam.py`:
```python
subprocess.run(["say", "-v", "Daniel", "-r", "190", text])
# or
subprocess.run(["say", "-v", "Aman", "-r", "180", text])
```

**Available voices:** `say -v '?' | grep en_`

## TTS Voice (Phone/Web)
- **Engine:** Browser Web Speech API
- **Default:** Auto-pick English male voice
- **Configurable:** Voice Settings panel (tap "Voice" in footer)
- **Settings:** Pitch (0.1-2.0), Speed (0.5-2.0), Voice dropdown

## Speech Recognition
- **Engine:** Google Speech-to-Text (via `speech_recognition` library locally, Web Speech API on phone)
- **Language:** en-US (supports Hinglish understanding)
- **Calibration:** 2 seconds ambient noise calibration on startup
- **Energy threshold:** 300 (adjustable — lower = more sensitive)

## Conversation Mode
After wake word, SAM stays active for **10 seconds** of silence.
- No need to say "SAM" again for follow-up questions
- "Thanks", "bye", "bas" → ends conversation, back to standby

## Emotion Detection
SAM detects user's mood from text and responds accordingly:
- **Angry** → Calm, apologetic
- **Happy** → Enthusiastic
- **Sad/Stressed** → Caring, supportive
- **Casual** → Friendly, warm
- **Serious** → Professional
- **Hurry** → Ultra short

Emotion saved with every conversation in `conversations.json`.

## Files
- `local_sam.py` — MacBook voice assistant
- `templates/index.html` — Phone web UI (voice handling in JS)
- `configs/voice_config.json` — Configurable settings
