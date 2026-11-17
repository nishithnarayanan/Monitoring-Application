"""HTTP routes for the Host Monitor demo."""

from __future__ import annotations

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_wtf import FlaskForm
from wtforms import (
    IntegerField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
)
from wtforms.validators import DataRequired, Length, NumberRange, Optional

from app import store
from app.auth import login_required, verify_credentials
from app.collector import check_connectivity, collect_for_server, collect_local
from app.metrics import panels_from_data, placeholder_metrics

bp = Blueprint("main", __name__)


class LoginForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[DataRequired(), Length(max=64)],
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(), Length(max=128)],
    )
    submit = SubmitField("Sign in")


class ServerForm(FlaskForm):
    name = StringField("Display name", validators=[DataRequired(), Length(max=128)])
    host = StringField("Hostname or IP", validators=[DataRequired(), Length(max=255)])
    ssh_port = IntegerField(
        "SSH port",
        default=22,
        validators=[DataRequired(), NumberRange(min=1, max=65535)],
    )
    ssh_username = StringField(
        "SSH username",
        validators=[DataRequired(), Length(max=64)],
    )
    auth_type = SelectField(
        "Auth",
        choices=[("password", "Password"), ("key", "Private key path")],
        validators=[DataRequired()],
    )
    password = PasswordField("SSH password", validators=[Optional(), Length(max=256)])
    key_path = StringField("Private key path", validators=[Optional(), Length(max=512)])
    submit = SubmitField("Add server")

    def validate(self, extra_validators=None) -> bool:
        ok = super().validate(extra_validators=extra_validators)
        if not ok:
            return False
        if self.auth_type.data == "password" and not (self.password.data or "").strip():
            self.password.errors.append("Password required for password auth.")
            return False
        if self.auth_type.data == "key" and not (self.key_path.data or "").strip():
            self.key_path.errors.append("Key path required for key auth.")
            return False
        return True


def _metrics_for_server_id(server_id: str | None) -> tuple[list[dict], dict | None]:
    """Collect metrics and refresh status when a server id is known."""
    if not server_id:
        return placeholder_metrics(), None

    secret_server = store.get_server(server_id, include_secret=True)
    public = store.get_server(server_id)
    if secret_server is None or public is None:
        return placeholder_metrics(), None

    data = collect_for_server(secret_server)
    if data.get("error"):
        store.update_server_status(server_id, status="unreachable")
    else:
        store.update_server_status(server_id, status="reachable")
    public = store.get_server(server_id)
    return panels_from_data(data), public


def _dashboard_metrics(servers: list[dict]) -> list[dict]:
    """Prefer first inventory server; else live localhost sample for the demo host."""
    if servers:
        panels, _ = _metrics_for_server_id(servers[0]["id"])
        # Refresh list statuses already updated for first; leave others as stored.
        return panels
    # No servers yet — still show local demo host cards when possible.
    return panels_from_data(collect_local())


@bp.get("/login")
@bp.post("/login")
def login():
    if session.get("user"):
        return redirect(url_for("main.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        if verify_credentials(form.username.data.strip(), form.password.data):
            session.clear()
            session["user"] = form.username.data.strip()
            session.permanent = False
            next_url = request.args.get("next") or url_for("main.dashboard")
            if not next_url.startswith("/"):
                next_url = url_for("main.dashboard")
            flash("Signed in successfully.", "success")
            return redirect(next_url)
        flash("Invalid username or password.", "error")

    return render_template("login.html", form=form)


@bp.post("/logout")
@login_required
def logout():
    session.clear()
    flash("Signed out.", "info")
    return redirect(url_for("main.login"))


@bp.get("/")
@login_required
def dashboard():
    form = ServerForm()
    metrics = _dashboard_metrics(store.list_servers())
    servers = store.list_servers()
    return render_template(
        "dashboard.html",
        servers=servers,
        metrics=metrics,
        form=form,
        refresh_seconds=10,
    )


@bp.post("/servers")
@login_required
def add_server():
    form = ServerForm()
    if form.validate_on_submit():
        auth_type = form.auth_type.data
        try:
            server = store.add_server(
                name=form.name.data.strip(),
                host=form.host.data.strip(),
                ssh_port=int(form.ssh_port.data),
                ssh_username=form.ssh_username.data.strip(),
                auth_type=auth_type,
                password=form.password.data if auth_type == "password" else None,
                key_path=form.key_path.data.strip() if auth_type == "key" else None,
            )
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("main.dashboard"))

        secret = store.get_server(server["id"], include_secret=True)
        ok = check_connectivity(
            host=secret["host"],
            port=int(secret["ssh_port"]),
            username=secret["ssh_username"],
            auth_type=secret["auth_type"],
            credential=secret.get("credential") or "",
        )
        store.update_server_status(
            server["id"],
            status="reachable" if ok else "unreachable",
        )
        flash(
            f"Added {server['name']} ({'reachable' if ok else 'unreachable'}).",
            "success" if ok else "error",
        )
        return redirect(url_for("main.dashboard"))

    for field, errors in form.errors.items():
        for err in errors:
            flash(f"{field}: {err}", "error")
    return redirect(url_for("main.dashboard"))


@bp.post("/servers/<server_id>/delete")
@login_required
def delete_server(server_id: str):
    if store.delete_server(server_id):
        flash("Server removed.", "info")
    else:
        flash("Server not found.", "error")
    return redirect(url_for("main.dashboard"))


@bp.get("/servers/<server_id>")
@login_required
def server_detail(server_id: str):
    metrics, server = _metrics_for_server_id(server_id)
    if server is None:
        return (
            render_template(
                "server_detail.html",
                server=None,
                server_id=server_id,
                metrics=placeholder_metrics(),
                refresh_seconds=None,
            ),
            404,
        )
    return render_template(
        "server_detail.html",
        server=server,
        server_id=server_id,
        metrics=metrics,
        refresh_seconds=10,
    )
