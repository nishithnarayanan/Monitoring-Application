"""SQLite inventory store for servers and admin credential hash."""

from __future__ import annotations

import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from flask import Flask, current_app, g

logger = logging.getLogger(__name__)

AUTH_PASSWORD = "password"
AUTH_KEY = "key"


def default_db_path() -> str:
    root = Path(__file__).resolve().parent.parent
    data_dir = root / "instance"
    data_dir.mkdir(mode=0o700, exist_ok=True)
    return str(data_dir / "monitoring.db")


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_db() -> Iterator[sqlite3.Connection]:
    db_path = current_app.config["DATABASE"]
    if "db" not in g:
        g.db = _connect(db_path)
    try:
        yield g.db
    finally:
        pass


def close_db(_: Any = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app: Flask) -> None:
    """Create tables and seed admin hash. Safe to call on every startup."""
    db_path = app.config["DATABASE"]
    Path(db_path).parent.mkdir(mode=0o700, exist_ok=True)
    conn = _connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS servers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                host TEXT NOT NULL,
                ssh_port INTEGER NOT NULL DEFAULT 22,
                ssh_username TEXT NOT NULL,
                auth_type TEXT NOT NULL CHECK (auth_type IN ('password', 'key')),
                credential_ref TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'unknown',
                last_update TEXT NOT NULL DEFAULT '—',
                created_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            "INSERT INTO meta(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            ("admin_username", app.config["ADMIN_USERNAME"]),
        )
        conn.execute(
            "INSERT INTO meta(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            ("admin_password_hash", app.config["ADMIN_PASSWORD_HASH"]),
        )
        conn.commit()
        try:
            os.chmod(db_path, 0o600)
        except OSError:
            logger.debug("Could not chmod database file (non-fatal)")
    finally:
        conn.close()


def _fernet():
    """Derive Fernet key from SECRET_KEY for SSH password blobs."""
    import base64
    import hashlib

    from cryptography.fernet import Fernet

    digest = hashlib.sha256(current_app.config["SECRET_KEY"].encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(token: str) -> str:
    return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")


def _row_to_server(row: sqlite3.Row, *, include_secret: bool = False) -> dict[str, Any]:
    data = {
        "id": str(row["id"]),
        "name": row["name"],
        "host": row["host"],
        "ssh_port": row["ssh_port"],
        "ssh_username": row["ssh_username"],
        "auth_type": row["auth_type"],
        "status": row["status"],
        "last_update": row["last_update"],
        "created_at": row["created_at"],
    }
    if include_secret:
        # Caller (SSH layer) only — never pass to templates/logs.
        if row["auth_type"] == AUTH_PASSWORD:
            data["credential"] = decrypt_secret(row["credential_ref"])
        else:
            data["credential"] = row["credential_ref"]  # key path ref
    else:
        # Redact: key auth exposes path only; password auth never shows secret.
        if row["auth_type"] == AUTH_KEY:
            data["credential_ref"] = row["credential_ref"]
        else:
            data["credential_ref"] = "[encrypted]"
    return data


def list_servers() -> list[dict[str, Any]]:
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM servers ORDER BY id ASC"
        ).fetchall()
    return [_row_to_server(r) for r in rows]


def get_server(server_id: str | int, *, include_secret: bool = False) -> dict[str, Any] | None:
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM servers WHERE id = ?",
            (int(server_id),),
        ).fetchone()
    if row is None:
        return None
    return _row_to_server(row, include_secret=include_secret)


def add_server(
    *,
    name: str,
    host: str,
    ssh_port: int = 22,
    ssh_username: str,
    auth_type: str,
    password: str | None = None,
    key_path: str | None = None,
) -> dict[str, Any]:
    if auth_type not in (AUTH_PASSWORD, AUTH_KEY):
        raise ValueError("auth_type must be 'password' or 'key'")
    if auth_type == AUTH_PASSWORD:
        if not password:
            raise ValueError("password required for password auth")
        credential_ref = encrypt_secret(password)
    else:
        if not key_path:
            raise ValueError("key_path required for key auth")
        # Path reference only — do not read or copy the private key file.
        credential_ref = str(Path(key_path).expanduser())
        try:
            # Best-effort reminder: key files should not be world-readable.
            if Path(credential_ref).is_file():
                mode = Path(credential_ref).stat().st_mode & 0o777
                if mode & 0o077:
                    logger.warning(
                        "SSH key path has overly permissive mode; prefer chmod 600"
                    )
        except OSError:
            pass

    created_at = datetime.now(timezone.utc).isoformat()
    with get_db() as db:
        cur = db.execute(
            """
            INSERT INTO servers (
                name, host, ssh_port, ssh_username, auth_type,
                credential_ref, status, last_update, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'unknown', '—', ?)
            """,
            (
                name.strip(),
                host.strip(),
                int(ssh_port),
                ssh_username.strip(),
                auth_type,
                credential_ref,
                created_at,
            ),
        )
        db.commit()
        new_id = cur.lastrowid
    # Never log password / key material.
    logger.info("Added server id=%s host=%s auth_type=%s", new_id, host, auth_type)
    return get_server(new_id)  # type: ignore[return-value]


def delete_server(server_id: str | int) -> bool:
    with get_db() as db:
        cur = db.execute("DELETE FROM servers WHERE id = ?", (int(server_id),))
        db.commit()
        deleted = cur.rowcount > 0
    if deleted:
        logger.info("Deleted server id=%s", server_id)
    return deleted


def update_server_status(
    server_id: str | int,
    *,
    status: str,
    last_update: str | None = None,
) -> None:
    if last_update is None:
        last_update = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    with get_db() as db:
        db.execute(
            "UPDATE servers SET status = ?, last_update = ? WHERE id = ?",
            (status, last_update, int(server_id)),
        )
        db.commit()


def get_meta(key: str) -> str | None:
    with get_db() as db:
        row = db.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return None if row is None else row["value"]
