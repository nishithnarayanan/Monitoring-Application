"""Session auth helpers for the demo admin user."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any

from flask import current_app, g, redirect, request, session, url_for
from werkzeug.security import check_password_hash


def login_required(view: Callable[..., Any]) -> Callable[..., Any]:
    """Redirect unauthenticated users to the login page."""

    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        if session.get("user") != current_app.config["ADMIN_USERNAME"]:
            return redirect(url_for("main.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def verify_credentials(username: str, password: str) -> bool:
    expected = current_app.config["ADMIN_USERNAME"]
    password_hash = current_app.config["ADMIN_PASSWORD_HASH"]
    if username != expected:
        return False
    return check_password_hash(password_hash, password)


def load_logged_in_user() -> None:
    g.user = session.get("user")
