"""Phase 1 auth unit tests. Fixtures use throwaway credentials only."""

from tests.conftest import TEST_PASSWORD, TEST_USERNAME


def test_unauthenticated_dashboard_redirects(client):
    res = client.get("/")
    assert res.status_code == 302
    assert "/login" in res.headers["Location"]


def test_unauthenticated_detail_redirects(client):
    res = client.get("/servers/1")
    assert res.status_code == 302
    assert "/login" in res.headers["Location"]


def test_valid_login_reaches_dashboard(client):
    res = client.post(
        "/login",
        data={"username": TEST_USERNAME, "password": TEST_PASSWORD},
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert b"Monitoring dashboard" in res.data
    assert b"Signed in successfully." in res.data
    assert TEST_USERNAME.encode() in res.data


def test_invalid_login_stays_on_login(client):
    res = client.post(
        "/login",
        data={"username": TEST_USERNAME, "password": "wrong-password"},
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert b"Invalid username or password" in res.data
    assert b"Sign in" in res.data


def test_logout_clears_session(auth_client):
    res = auth_client.post("/logout", follow_redirects=False)
    assert res.status_code == 302
    assert "/login" in res.headers["Location"]

    res = auth_client.get("/")
    assert res.status_code == 302
    assert "/login" in res.headers["Location"]
