"""Shared pytest fixtures. Uses throwaway secrets and a temp SQLite DB."""

import pytest
from werkzeug.security import generate_password_hash

from app import create_app

TEST_USERNAME = "admin"
TEST_PASSWORD = "test-password-only"


@pytest.fixture
def app(tmp_path):
    db_path = tmp_path / "test-monitoring.db"
    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret-not-for-prod",
            "ADMIN_USERNAME": TEST_USERNAME,
            "ADMIN_PASSWORD_HASH": generate_password_hash(TEST_PASSWORD),
            "WTF_CSRF_ENABLED": False,
            "DATABASE": str(db_path),
        }
    )
    yield application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client):
    """Test client already signed in as the demo admin."""
    client.post(
        "/login",
        data={"username": TEST_USERNAME, "password": TEST_PASSWORD},
        follow_redirects=False,
    )
    return client
