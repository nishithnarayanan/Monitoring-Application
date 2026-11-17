"""HTTP routes for the monitoring demo."""

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
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Length

from app.auth import login_required, verify_credentials
from app.metrics import placeholder_metrics
from app import store

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
    servers = store.list_servers()
    return render_template(
        "dashboard.html",
        servers=servers,
        metrics=placeholder_metrics(),
    )


@bp.get("/servers/<server_id>")
@login_required
def server_detail(server_id: str):
    server = store.get_server(server_id)
    metrics = placeholder_metrics()
    if server is None:
        return (
            render_template(
                "server_detail.html",
                server=None,
                server_id=server_id,
                metrics=metrics,
            ),
            404,
        )
    return render_template(
        "server_detail.html",
        server=server,
        server_id=server_id,
        metrics=metrics,
    )
