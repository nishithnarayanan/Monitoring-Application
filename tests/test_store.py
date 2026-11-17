"""Phase 2 storage unit tests. Temp DB only; no real credentials in fixtures."""

import logging

from app import store


def test_add_list_remove_server(app):
    with app.app_context():
        assert store.list_servers() == []

        created = store.add_server(
            name="web-1",
            host="10.0.0.5",
            ssh_port=22,
            ssh_username="ubuntu",
            auth_type="password",
            password="not-a-real-secret",
        )
        assert created["name"] == "web-1"
        assert created["host"] == "10.0.0.5"
        assert created["auth_type"] == "password"
        assert created["credential_ref"] == "[encrypted]"

        listed = store.list_servers()
        assert len(listed) == 1
        assert listed[0]["id"] == created["id"]

        assert store.delete_server(created["id"]) is True
        assert store.list_servers() == []
        assert store.delete_server(created["id"]) is False


def test_key_path_stored_as_ref_only(app):
    with app.app_context():
        created = store.add_server(
            name="db-1",
            host="10.0.0.6",
            ssh_username="ops",
            auth_type="key",
            key_path="~/keys/demo.pem",
        )
        assert created["auth_type"] == "key"
        assert "demo.pem" in created["credential_ref"]
        # Public list must not invent a password field.
        assert "credential" not in created


def test_password_not_logged_plaintext(app, caplog):
    with app.app_context():
        secret = "super-secret-ssh-pass-xyz"
        with caplog.at_level(logging.INFO, logger="app.store"):
            store.add_server(
                name="log-check",
                host="10.0.0.7",
                ssh_username="ops",
                auth_type="password",
                password=secret,
            )
        joined = " ".join(r.getMessage() for r in caplog.records)
        assert secret not in joined


def test_admin_hash_seeded_in_meta(app):
    with app.app_context():
        username = store.get_meta("admin_username")
        password_hash = store.get_meta("admin_password_hash")
        assert username == "admin"
        assert password_hash
        assert not password_hash.startswith("test-password")
        assert "test-password-only" not in password_hash
