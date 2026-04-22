# Office Mode

## Overview
SAM ka work mode — Slack, projects, tasks, aur coding ke liye.

## Activation
- Voice: "SAM switch to office mode" / "office mode" / "office karo"
- UI: Footer mein mode label orange ho jayega

## Deactivation
- "Switch to home mode" / "normal mode" / "home karo"

---

## Features

### 1. Slack Integration
| Command | Tag | Description |
|---------|-----|-------------|
| "Product automation ke messages padho" | `[SLACK_READ: product_automation]` | Channel ke latest messages read kare |
| "Rohit ko message karo ki done ho gaya" | `[SLACK_SEND: product_automation, done ho gaya]` | Channel mein message bheje |
| "Slack pe scraping search karo" | `[SLACK_SEARCH: scraping]` | Messages search kare across channels |

**Requirements:**
- `SLACK_BOT_TOKEN` environment variable
- Bot scopes: `channels:history`, `channels:read`, `chat:write`, `search:read`, `users:read`

### 2. Project Knowledge
SAM ko 10 projects ki info embedded hai. User bole toh project status, tech stack, path sab bata sakta hai.

| Command | Tag |
|---------|-----|
| "Optimus ka status kya hai?" | `[PROJECT_INFO: optimus]` |
| "Price benchmark kya hai?" | `[PROJECT_INFO: price_benchmark]` |

### 3. Pending Tasks
Slack se tracked tasks. User bole "kya pending hai" toh list dikha de.

| Command | Tag |
|---------|-----|
| "Mere pending tasks batao" | `[PENDING_TASKS]` |

### 4. Optimus Widget Creation
Manoj ki jagah SAM widgets banata hai via Optimus API.

See: [optimus_integration.md](optimus_integration.md)

### 5. Code & Automation
Claude Code CLI se code likhwana aur run karwana.

See: [macbook_agent.md](macbook_agent.md)

---

## Technical Flow
```
User speaks → [OFFICE MODE] prefix added → Gemini/Claude processes
→ Command tags parsed → Server executes (Slack API / Optimus API / Agent)
→ Results fed back to AI → Final response spoken
```

## Files
- `office.py` — Slack functions + project knowledge + pending tasks
- `optimus_agent.py` — Optimus widget CRUD via API
