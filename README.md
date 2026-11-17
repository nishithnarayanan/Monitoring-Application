# Demo Monitoring Infrastructure

Local Flask demo that will show read-only Linux server metrics (CPU, memory, network, ports) over SSH.

**Current:** Phase 0–2 — Host Monitor UI (metric placeholders), sign-in, SQLite inventory store.

## Local run

```bash
cd "<project-root>"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
flask --app app run --host 127.0.0.1 --port 5080
```

Open **http://127.0.0.1:5080** — you will be redirected to sign in.

> If port `5000` is already in use on this machine, use `5080` (or any free port).

### Demo credentials

| Field | Default |
|-------|---------|
| Username | `admin` |
| Password | `changeme` |

Change them via env (see `.env.example`):

```bash
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
export DEMO_ADMIN_PASSWORD='your-local-password'
```

### Local data (SQLite)

- DB file: `instance/monitoring.db` (created on first run; mode `600` when possible)
- Stores: admin username + password **hash**, and server inventory
- SSH passwords are stored **encrypted** (Fernet derived from `SECRET_KEY`)
- SSH private keys are stored as a **path reference only** (file is not copied)
- Directory `instance/` is gitignored — local-only, not for production

Add/remove UI arrives in Phase 3; the store helpers are ready now.

## Running tests

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
```

Tests use throwaway `SECRET_KEY` / password fixtures and a **temporary SQLite file** per test session (never the real `instance/` DB). CSRF is disabled in the test client.

## Security (demo)

- Bind to **127.0.0.1** only — do not use `0.0.0.0`.
- `SECRET_KEY` from env when possible; session cookie is HttpOnly + SameSite=Lax.
- Login form is CSRF-protected (Flask-WTF).
- Dashboard and server pages require a signed-in session.
- Never commit `.env`, `instance/*.db`, or real secrets.
- Credential material is not written to application logs.
- Not production-hardened (no HTTPS, single shared admin).

## Layout

```
app/
  __init__.py      # create_app() + CSRF + DB init
  auth.py          # login_required, credential check
  store.py         # SQLite inventory helpers
  routes.py        # login/logout + dashboard/detail
  templates/
  static/style.css
instance/          # local SQLite (gitignored)
tests/
docs/
```
