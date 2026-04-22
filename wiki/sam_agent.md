# SAM Agent — MacBook Background Service

## Overview
MacBook pe background mein chalta hai. Proactive alerts, scheduled tasks, Gmail, Sheets, error monitoring sab handle karta hai.

## Start
```bash
cd ~/Desktop/Personal/ai\ bot
source venv/bin/activate
python sam_agent.py
```

## Features

### 1. Proactive Alerts (Every 1 hour)
- Slack scan kare — Satyam ko mention hua toh alert
- Last 4 hours ke messages check kare
- Console pe print kare alerts

### 2. Scheduled Tasks
| Time | Task |
|------|------|
| 9:00 AM | Morning Summary — overnight Slack, pending tasks |
| 6:00 PM | Evening Report — din bhar ka summary |
| Every 1 hour | Alert check |
| Every 3 hours | Health check (servers, APIs) |

### 3. Gmail
- Via Claude CLI (Satyam ka Max plan)
- Read unread emails, summarize
- Draft replies

### 4. Google Sheets
- Service account: `sam-bot@widget-474311.iam.gserviceaccount.com`
- Read any shared sheet
- Analyze data via Groq
- Write/append rows
- Credentials: `credentials/google-service-account.json`

### 5. Error Monitoring (Every 3 hours)
| Service | Check |
|---------|-------|
| Render server | https://jarvis-ai-wsds.onrender.com/health |
| Optimus | https://optimus-app-hazel.vercel.app/api/local/widgets |
| Google Sheets | Connection status |
| Groq API | Key status |

### 6. Quick Actions
| Function | Usage |
|----------|-------|
| `quick_daily_report()` | Send daily summary |
| `quick_sheet_summary(url)` | Analyze a sheet |
| `quick_remind(user_id, msg)` | Remind someone on Slack |

## Logs
Agent events stored in `sam_agent_logs.json`:
- Agent start/stop
- Alert checks
- Health checks
- Summaries generated

## Files
- `sam_agent.py` — Main agent script
- `credentials/google-service-account.json` — Google auth
- `sam_agent_logs.json` — Event logs (auto-created)
