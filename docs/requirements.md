# PRD: Demo Monitoring Infrastructure (Linux Servers)

## 1. Overview

A local demo Flask app that shows real-time Linux server metrics in a read-only UI so L1/L2/L3 and app teams do not need to SSH in for basic checks.

**Goal:** Local demo only — minimal setup, not production-ready.

## 2. Problem

Today, checking live CPU, memory, network, and port usage requires logging into each server. This is slow and inconsistent across teams.

## 3. Users

Internal teams only:

- L1 / L2 / L3 infrastructure support
- Application development groups

All users share one demo admin account. No roles or SSO.

## 4. Goals / Non-Goals

### Goals

- Sign in with a default admin user
- Add Linux servers to monitor
- View live CPU, memory, network, and listening ports in a simple UI
- Run locally with short setup steps

### Non-Goals (out of scope)

- Alerting / notifications
- Historical charts or long-term storage
- Windows or non-Linux hosts
- Multi-user RBAC / SSO
- HTTPS / production hardening
- Agent install on target hosts (beyond SSH access)

## 5. Assumptions (defaults)

| Area | Default |
|------|---------|
| Collection | Agentless over SSH from the Flask app |
| Auth | Single user `admin` with hashed password (seeded at first run / config) |
| Metrics | CPU %, memory used/total, network I/O, listening ports |
| UI | Server list dashboard → detail page; auto-refresh ~10s |
| Write actions | Metrics are read-only; admin may add/remove servers |
| Deploy | Local `venv` + `pip install` + `flask run` |

## 6. Features

### F1 — Read-only, user-friendly UI

- Clean dashboard listing monitored servers (name, host, status, last update)
- Server detail page with CPU, memory, network, and listening ports
- Metrics views are read-only (no remote config changes from the UI)
- Auto-refresh approximately every 10 seconds (manual refresh also OK)

### F2 — Sign-in

- Default username: `admin`
- Password stored hashed (e.g. Werkzeug / bcrypt)
- Seeded via config or first-run default for the demo
- Unauthenticated users cannot see metrics or manage servers

### F3 — Add Linux servers

Required fields when adding a server:

- Display name
- Hostname or IP
- SSH port (default `22`)
- SSH username
- Auth: password **or** private key path

Capabilities:

- Add / remove servers from the UI (admin session)
- Show reachable / unreachable status after a connectivity check

## 7. Metrics (per server)

| Metric | Display |
|--------|---------|
| CPU | Usage % |
| Memory | Used / total (and %) |
| Network | Basic RX/TX rates or counters |
| Ports | Listening ports (port + process if available) |

Collection runs over SSH using standard Linux commands (e.g. `/proc`, `ss`/`netstat`). Failures show a clear error/unreachable state.

## 8. Tech stack

- **Backend:** Python + Flask
- **Frontend:** Flask templates + attractive CSS (simple modern UI; no heavy SPA required)
- **Auth:** Session login; hashed password
- **Storage:** Lightweight local store (SQLite or JSON file) for server inventory and admin credential hash
- **Remote access:** Paramiko (or equivalent) for SSH

## 9. Local run (minimal)

```bash
cd "<project-root>"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask --app app run
```

Open `http://127.0.0.1:5000`, sign in as `admin` with the demo password from README/config.

## 10. Success criteria

- Can log in as `admin`
- Can add at least one Linux server (local or remote with SSH)
- Dashboard and detail page show CPU, memory, network, and listening ports without SSH-ing manually
- UI remains read-only for metrics; setup stays local and short

## 11. Open items (optional later)

- Disk usage / load average
- Tags or grouping of servers
- Docker Compose packaging
