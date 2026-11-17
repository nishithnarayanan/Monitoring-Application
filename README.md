# Host Monitor (Demo Monitoring Infrastructure)

Local Flask demo: read-only Linux host metrics (CPU, memory, disk, load, network, ports, processes) with a simple inventory UI.

**Stack:** Flask + SQLite + Paramiko (agentless SSH) · local `venv` only.

## Local run

```bash
cd "<project-root>"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
flask --app app run --host 127.0.0.1 --port 5080
```

Open **http://127.0.0.1:5080** (use another port if busy).

### Demo credentials

| Field | Default |
|-------|---------|
| Username | `admin` |
| Password | `changeme` |

```bash
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
export DEMO_ADMIN_PASSWORD='your-local-password'
```

### UI walkthrough

1. Sign in → green **Signed in successfully.**
2. **Servers** panel → add a host (name, host/IP, SSH port, user, password **or** key path).
3. Quick demo: host `127.0.0.1` collects metrics on this machine without SSH.
4. Metric cards fill with live data; detail page uses the same seven cards.
5. Auto-refresh ~10s; metrics are read-only.

### Add server fields

| Field | Notes |
|-------|--------|
| Display name | Shown in the Servers table |
| Hostname or IP | `127.0.0.1` / `localhost` uses local collectors |
| SSH port | Default `22` |
| SSH username | Remote login user |
| Auth | Password **or** private key path (not both required) |

SSH passwords are stored encrypted; key paths are references only (file not copied). Credentials are never shown again in the UI.

### Local data

- SQLite: `instance/monitoring.db` (mode `600` when possible, gitignored)
- Bind **127.0.0.1** only — not production-hardened (no HTTPS)

## Running tests

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
```

Tests use throwaway secrets and a **temporary SQLite file**. Parser tests are offline (sample `/proc` / `df` / `ss` / `ps` text). CSRF is disabled in the test client.

## CI

GitHub Actions (`.github/workflows/ci.yml`) runs `pytest` on push/PR to `main`.

## Smoke check

1. `flask --app app run --host 127.0.0.1 --port 5080`
2. Login as `admin` / `changeme`
3. Add server `127.0.0.1` → status reachable → cards show CPU/memory/disk/load/network/ports/processes
4. Open server detail → same cards
5. Remove server → empty Servers panel copy returns

## Security (demo)

- Localhost bind only
- Hashed admin password; CSRF on forms; HttpOnly session cookie
- No secrets in git; never log SSH passwords
- Fixed remote/local command strings (no shell injection of user input)
- Not for production

## Layout

```
app/
  __init__.py   auth.py   store.py   collector.py   metrics.py   routes.py
  templates/    static/style.css
instance/       # local SQLite (gitignored)
tests/
.github/workflows/ci.yml
docs/
```
