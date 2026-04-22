# Home Mode

## Overview
SAM ka default mode — personal assistant for everyday tasks.

## Activation
Default mode. Ya bolo: "switch to home mode" / "normal mode"

---

## Features

### 1. Weather
| Command | Tag |
|---------|-----|
| "Weather kaisa hai?" | `[WEATHER]` |
| "Mumbai ka weather" | `[WEATHER: Mumbai]` |
| "Kal ka weather" | `[WEATHER]` (forecast included) |

**Source:** wttr.in (free, no API key)
**Data:** temp, feels_like, humidity, wind, today max/min, tomorrow forecast

### 2. News
| Command | Tag |
|---------|-----|
| "Aaj ki news sunao" | `[NEWS]` |
| "Cricket ki news" | `[NEWS: cricket]` |
| "Tech news batao" | `[NEWS: technology]` |

**Source:** Google News RSS (free, no API key)
**Returns:** 5 headlines by default

### 3. Music & Radio
| Command | Tag |
|---------|-----|
| "Play Arijit Singh" | `[PLAY_SONG: Arijit Singh]` |
| "Bollywood radio lagao" | `[RADIO: bollywood]` |
| "Lofi music chalao" | `[RADIO: lofi]` |

**Radio genres:** bollywood, lofi, english, hindi, news, devotional
**Opens:** YouTube in browser

### 4. Timer & Reminders
| Command | Tag |
|---------|-----|
| "5 minute ka timer" | `[TIMER: 300]` |
| "30 min mein yaad dila dena meeting" | `[REMINDER: 30, meeting]` |

**Handled on phone browser** — notification + beep sound

### 5. Smart Home (Tuya/SmartLife)
| Command | Tag |
|---------|-----|
| "Bedroom light off" | `[DEVICE: bedroom_light, OFF]` |
| "Sab lights band karo" | Multiple `[DEVICE: ...]` tags |
| "Hall fan on" | `[DEVICE: hall_fan, ON]` |

**Requires:** Tuya credentials + device IDs in devices.json

### 6. Play Store
| Command | Tag |
|---------|-----|
| "Install Spotify" | `[PLAY_STORE: Spotify]` |

**Opens:** Play Store page in browser

### 7. Web Search
| Command | Tag |
|---------|-----|
| "Search Python tutorial" | `[WEB_SEARCH: Python tutorial]` |
| "India cricket score" | `[WEB_SEARCH: India cricket score live]` |

### 8. General Knowledge
No tags needed — SAM answers directly:
- Math: "100 ka 18% GST?"
- Jokes: "Ek joke sunao"
- Translation: "Hello ko Japanese mein kya bolte hain?"
- Recipes: "Dal kaise banate hain?"
- Facts: "Capital of Japan?"

---

## Routines
| Trigger | What SAM does |
|---------|-----------------|
| "Good morning" | Weather + News + Lights on |
| "Good night" | All lights/fans off |
| "Movie time" | Lights off + suggest something |

## Files
- `services.py` — Weather, news, radio functions
- `smart_home.py` — Tuya device control
- `devices.json` — Device registry
- `tasks.py` — Command tag parser
