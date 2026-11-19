"""Flask application factory for the monitoring demo."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from flask import Flask
from flask_wtf import CSRFProtect
from werkzeug.security import generate_password_hash

csrf = CSRFProtect()


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__)

    # Local-demo defaults. Prefer env for SECRET_KEY and demo password.
    demo_password = os.environ.get("DEMO_ADMIN_PASSWORD", "changeme")
    password_hash = os.environ.get("ADMIN_PASSWORD_HASH") or generate_password_hash(
        demo_password
    )
    default_db = str(
        Path(__file__).resolve().parent.parent / "instance" / "monitoring.db"
    )

    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
        ADMIN_USERNAME=os.environ.get("ADMIN_USERNAME", "admin"),
        ADMIN_PASSWORD_HASH=password_hash,
        DATABASE=os.environ.get("DATABASE", default_db),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        WTF_CSRF_ENABLED=True,
        DEBUG=True,
    )

    if test_config is not None:
        app.config.update(test_config)

    csrf.init_app(app)

    from app import store
    from app.auth import load_logged_in_user
    from app.routes import bp

    store.init_db(app)
    app.teardown_appcontext(store.close_db)

    app.before_request(load_logged_in_user)
    app.register_blueprint(bp)
    return app
