# TODO: Demo Monitoring Infrastructure

Small, AI-friendly increments for a local Flask demo. Check items off as you go.

---

## Phase 0 — Project initialization & basic UI

### 0.1 Scaffold the app
- [x] Create Flask app layout: `app/__init__.py`, `app/routes.py`, `templates/`, `static/`
- [x] Add `requirements.txt` with Flask (pin a recent stable version)
- [x] Add `.gitignore` (`.venv/`, `__pycache__/`, `*.pyc`, `.env`, local DB/JSON)
- [x] **Docs:** Add root `README.md` with local run steps (`venv`, `pip install`, `flask run`)
- [x] **Security:** Never commit secrets; keep demo password out of git (use `.env` or config example only)

### 0.2 Basic UI shell
- [x] Add base Jinja template with simple modern CSS (`static/style.css`)
- [x] Add home/dashboard page route returning a static “Monitored servers” list (placeholder rows OK)
- [x] Add placeholder server detail page route/template
- [x] Host Monitor dashboard layout: Servers panel + metric cards (CPU, Memory, Disk, Load, Network, Ports, Processes) as “No data yet”
- [x] **Docs:** Note in README how to open `http://127.0.0.1:5000`
- [x] **Security:** Ensure debug defaults are documented as local-only; no public bind (`127.0.0.1`)

---

## Phase 1 — Sign-in & unit tests

### 1.1 Auth foundation
- [x] Add config for admin username + password hash (env/config; seed default `admin` on first run)
- [x] Hash passwords with Werkzeug (or bcrypt); never store plaintext
- [x] Implement login form + session-based sign-in / sign-out
- [x] Protect dashboard and detail routes (redirect unauthenticated users to login)
- [x] **Docs:** Document default demo credentials in README (and how to change them)
- [x] **Security:** Use Flask `SECRET_KEY` from env; HttpOnly session cookie; CSRF on login form if using WTForms/Flask-WTF

### 1.2 Auth unit tests
- [x] Add `pytest` (+ Flask test client) to `requirements.txt` / `requirements-dev.txt`
- [x] Test: unauthenticated access redirects to login
- [x] Test: valid credentials create a session and reach dashboard
- [x] Test: invalid credentials stay on login with error
- [x] Test: logout clears session
- [x] **Docs:** Add “Running tests” section (`pytest`)
- [x] **Security:** Tests use a throwaway secret/password; no real credentials in fixtures

---

## Phase 2 — Local storage for servers

### 2.1 Inventory store
- [x] Choose SQLite (preferred) or JSON file for server inventory + admin hash
- [x] Define server fields: name, host, SSH port, username, auth type, credential ref
- [x] Implement create / list / delete helpers
- [x] **Docs:** Document where data lives on disk and that it is local-only
- [x] **Security:** Store SSH passwords/keys encrypted or as path refs only; never log credentials; restrict file perms if using a key path

### 2.2 Storage tests
- [x] Unit tests for add / list / remove server records
- [x] **Docs:** Mention test DB uses a temp file/in-memory store
- [x] **Security:** Assert secrets are not written in plaintext logs during tests

---

## Phase 3 — Add / remove servers UI (Host Monitor Servers panel)

Keep the existing Host Monitor look: dashed **Servers** panel on the dashboard, `admin` pill, metric cards stay as “No data yet” until Phase 5.

### 3.1 Manage servers
- [x] Add “Add server” controls inside the dashboard **Servers** panel (name, host, port default 22, SSH user, password **or** key path)
- [x] Wire form to SQLite inventory store; flash success/validation errors (same flash style as “Signed in successfully.”)
- [x] Add remove-server action per row (POST + confirm); table columns stay Name / Host / Status / Last update
- [x] After add: run a simple SSH connectivity check stub → status `reachable` / `unreachable` in the panel
- [x] Empty state copy: only show “No servers yet…” when inventory is empty; otherwise list rows
- [x] **Docs:** Document required fields and auth options in README (Host Monitor local demo)
- [x] **Security:** Require login for all manage actions; validate/sanitize inputs; use POST for mutations; CSRF on forms; never echo SSH password/key material in HTML

### 3.2 Manage-server tests
- [x] Test: cannot add/remove without login
- [x] Test: add server with valid fields appears in the Servers panel on the dashboard
- [x] Test: remove server deletes from store and panel
- [x] Test: dashboard still renders all seven metric cards as “No data yet” after add/remove
- [x] **Docs:** Update test notes if new fixtures were added
- [x] **Security:** Confirm credentials submitted in forms are not echoed back in HTML

---

## Phase 4 — Metrics collection (fill Host Monitor cards)

Collect data for every dashboard card already defined in `app/metrics.py` / the snip.

| Card | Target display |
|------|----------------|
| CPU | Overall usage % |
| Memory | Used / free (and % if easy) |
| Disk | Root filesystem used/total or % |
| Load average | 1 / 5 / 15 min |
| Network | RX / TX |
| Listening ports | TCP / UDP (port + process if available) |
| Processes | Top by CPU / memory (short list) |

### 4.1 SSH / local collector
- [x] Add Paramiko (or equivalent) dependency for remote hosts
- [x] Implement connect helper (password **or** private key path from store)
- [x] Prefer read-only commands (`/proc`, `df`, `ss`/`netstat`, `ps`); optional localhost path without SSH for the demo host
- [x] Map output into a metrics dict keyed like the UI: `cpu`, `memory`, `disk`, `load`, `network`, `ports`, `processes`
- [x] On timeout/failure: mark server `unreachable` and leave card values as error / “No data yet”
- [x] **Docs:** Document agentless SSH collection and that the Host Monitor UI is read-only
- [x] **Security:** Short timeouts; no shell injection; never log or return SSH secrets; careful key path handling

### 4.2 Metrics unit tests
- [x] Unit-test parsers with sample `/proc`, `df`, `ss`, `ps` output (no real SSH required)
- [x] Assert parsed dict includes all seven keys used by the Host Monitor cards
- [x] Test unreachable / timeout path returns a clear error state
- [x] **Docs:** Note how to run parser tests offline
- [x] **Security:** Fixtures contain no real host credentials

---

## Phase 5 — Live Host Monitor dashboard & detail UI

Replace placeholders only — keep brand, Servers panel, and card layout from Phase 0.

### 5.1 Wire metrics into existing cards
- [x] Dashboard Servers panel: name, host, status, last update from live/cached collection
- [x] Dashboard metric grid: fill **CPU, Memory, Disk, Load average, Network, Listening ports, Processes** (same subtitles as the snip); use “No data yet” only when missing
- [x] Detail page: reuse the same seven-card grid for the selected server
- [x] Auto-refresh ~10s (meta refresh or light JS); keep manual refresh
- [x] Metrics views remain read-only (no remote config changes from the UI)
- [x] **Docs:** Short UI walkthrough in README (Host Monitor → sign-in → Servers → metric cards)
- [x] **Security:** Escape all template output; never show SSH passwords/keys on UI

### 5.2 End-to-end smoke (local)
- [x] Manual check: login (`Signed in successfully.`) → add server in Servers panel → cards show live values
- [x] **Docs:** Minimal “smoke check” bullets in README (port `5080` if `5000` is busy)
- [x] **Security:** Confirm app binds to localhost only for the demo

---

## Phase 6 — CI/CD (GitHub Actions)

### 6.1 Continuous integration
- [x] Add `.github/workflows/ci.yml`
- [x] On push/PR: install deps, run `pytest`, fail on test errors
- [x] Optionally run a basic lint (`ruff` or `flake8`) if already in deps
- [x] **Docs:** Badge or short “CI” note in README
- [x] **Security:** No secrets in workflow logs; use GitHub secrets only if later needed; pin action versions

### 6.2 Local-only deploy note (no cloud)
- [x] Keep deploy as local `flask run --host 127.0.0.1` only (demo scope)
- [x] **Docs:** Reaffirm local-only Host Monitor deploy; no production/HTTPS steps
- [x] **Security:** Document that this is not production-hardened

---

## Phase 7 — Polish & success criteria

### 7.1 Final checklist (Host Monitor + PRD)
- [x] Can log in as `admin` and see “Signed in successfully.”
- [x] Can add at least one Linux server in the Servers panel (local or remote SSH)
- [x] Dashboard shows all seven cards with live data: CPU, Memory, Disk, Load average, Network, Listening ports, Processes
- [x] Detail page matches the same card set for a selected server
- [x] Metrics UI is read-only; setup stays short (`venv` + `pip` + `flask run`)
- [x] **Docs:** README matches actual commands, default password, and UI labels
- [x] **Security:** Quick pass — hashed password, protected routes, no secrets in repo, localhost bind

### 7.2 Optional later (still out of scope)
- [ ] Tags or grouping of servers
- [ ] Docker Compose packaging
- [ ] Historical charts / alerting

---

## Suggested order for AI-assisted sessions

1. Phase 0 (init + Host Monitor UI shell) — done  
2. Phase 1 (sign-in + auth tests) — done  
3. Phase 2 (SQLite storage) — done  
4. Phase 3 (add/remove in Servers panel) — done  
5. Phase 4 (collect all seven metric card values) — done  
6. Phase 5 (wire live data into Host Monitor cards) — done  
7. Phase 6 (GitHub Actions CI) — done  
8. Phase 7 (success criteria) — done  

One phase (or even one `###` subsection) per AI session is ideal.
