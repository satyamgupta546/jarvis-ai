# Conversation Storage

## Overview
Saari conversations store hoti hain with emotion, mode, timestamp — JSON file mein.

## Storage File
```
/Users/satyam/Desktop/Personal/ai bot/conversations.json
```

## Data Format
```json
{
  "conversations": [
    {
      "id": 1,
      "timestamp": "2026-04-18T18:30:00.123456",
      "date": "2026-04-18",
      "time": "18:30:00",
      "mode": "office",
      "emotion": "serious",
      "user": "pending tasks batao",
      "sam": "Sir, 8 pending tasks hain. Sabse important Diksha ka AMS automation hai."
    }
  ],
  "stats": {
    "total": 42,
    "by_emotion": {
      "happy": 10,
      "serious": 15,
      "casual": 12,
      "angry": 5
    },
    "by_mode": {
      "home": 25,
      "office": 17
    }
  }
}
```

## Fields

### Conversation Entry
| Field | Type | Description |
|-------|------|-------------|
| id | int | Auto-increment ID |
| timestamp | string | ISO 8601 full timestamp |
| date | string | YYYY-MM-DD (for daily filtering) |
| time | string | HH:MM:SS |
| mode | string | "home" or "office" |
| emotion | string | Detected emotion of user |
| user | string | What user said |
| sam | string | Full SAM response (including tags) |

### Emotions Tracked
| Emotion | Trigger Examples |
|---------|-----------------|
| happy | "amazing", "bahut accha", "maza aa gaya" |
| angry | "kya bakwas", frustration, "kaam nahi karta" |
| sad | "bore ho gaya", "thak gaya" |
| stressed | "bahut kaam", "deadline" |
| casual | "yaar", "bhai", friendly tone |
| serious | Professional, direct commands |
| hurry | "jaldi", "quick", "fast" |
| neutral | Normal conversation |

### Stats
| Field | Description |
|-------|-------------|
| total | Total conversations ever |
| by_emotion | Count per emotion type |
| by_mode | Count per mode (home/office) |

## Limits
- **Max stored:** 1000 conversations (oldest removed when exceeded)
- **File size:** ~500KB for 1000 conversations

## Methods (ConversationStore class)
| Method | Description |
|--------|-------------|
| `save(user, sam, mode, emotion)` | Save a conversation entry |
| `get_today()` | Get all conversations from today |
| `get_stats()` | Get aggregated stats |

## Files
- `local_sam.py` — ConversationStore class
- `conversations.json` — Data file (auto-created)
