"""Auto-refresh toggle tests."""


def test_auto_refresh_defaults_on(auth_client):
    res = auth_client.get("/")
    assert res.status_code == 200
    assert b"Auto-refresh: On" in res.data
    assert b'http-equiv="refresh"' in res.data


def test_toggle_turns_auto_refresh_off(auth_client):
    res = auth_client.post(
        "/settings/auto-refresh",
        data={"next": "/"},
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert b"Auto-refresh: Off" in res.data
    assert b'http-equiv="refresh"' not in res.data


def test_toggle_twice_turns_auto_refresh_back_on(auth_client):
    for _ in range(2):
        res = auth_client.post(
            "/settings/auto-refresh",
            data={"next": "/"},
            follow_redirects=True,
        )
    assert res.status_code == 200
    assert b"Auto-refresh: On" in res.data
    assert b'http-equiv="refresh"' in res.data


def test_toggle_requires_login(client):
    res = client.post("/settings/auto-refresh", follow_redirects=False)
    assert res.status_code == 302
    assert "/login" in res.headers["Location"]
