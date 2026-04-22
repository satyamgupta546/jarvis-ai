# MacBook Agent

## Overview
MacBook pe run hone wala agent — SAM ko file access, code execution, aur system control deta hai.

## Start Agent
```bash
cd ~/Desktop/Personal/ai\ bot
source venv/bin/activate
python agent.py                              # connects to localhost
python agent.py wss://your-server.com        # connects to cloud server
```

## Authentication
- **Token:** `AGENT_TOKEN` (default: `sam-secret-2026`)
- WebSocket endpoint: `/ws/agent?token=<token>`
- Auto-reconnects on disconnect (5s retry)

---

## Commands

### 1. Read File
```json
{"type": "read_file", "path": "~/Desktop/code/optimus/package.json"}
```
- Max 500KB
- Blocked paths: .ssh, .env, credentials, secrets, passwords, tokens

### 2. List Files
```json
{"type": "list_files", "path": "~/Desktop/code"}
```
- Max 100 entries returned
- Returns: name, is_dir, size

### 3. Open App
```json
{"type": "open_app", "app": "Safari"}
```
- macOS: `open -a <app>`
- Works with any installed app

### 4. System Info
```json
{"type": "system_info"}
```
- Returns: CPU %, RAM %, disk %, battery %, platform, hostname

### 5. Write File
```json
{"type": "write_file", "path": "~/Desktop/code/test.py", "content": "print('hello')"}
```
- Creates parent directories automatically
- Blocked: sensitive paths

### 6. Run Command
```json
{"type": "run_command", "command": "pip install pandas", "cwd": "~/Desktop/code"}
```
- 60 second timeout
- Blocked: `rm -rf /`, `mkfs`, `dd if=`, destructive commands
- Returns: stdout, stderr, returncode

### 7. Claude Code CLI
```json
{"type": "claude_code", "prompt": "Create a Python script that...", "cwd": "~/Desktop/code"}
```
- Uses Satyam's $20/month Max plan — no API credits
- 5 minute timeout
- Runs: `claude -p --output-format text <prompt>`

### 8. Create Project
```json
{"type": "create_project", "name": "my-project", "files": {"main.py": "code...", "utils/helper.py": "code..."}}
```
- Creates folder at `~/Desktop/code/<name>/`
- Creates all files with content

---

## Security
- Sensitive paths blocked (.ssh, .env, credentials, etc.)
- Dangerous commands blocked (rm -rf /, mkfs, etc.)
- Max file read: 500KB
- Command timeout: 60s (300s for Claude Code)
- Token-based authentication

## Files
- `agent.py` — MacBook agent (standalone script)
