"""Phase 3 manage-server tests."""


def test_cannot_add_without_login(client):
    res = client.post(
        "/servers",
        data={
            "name": "x",
            "host": "127.0.0.1",
            "ssh_port": 22,
            "ssh_username": "u",
            "auth_type": "password",
            "password": "secret-should-not-echo",
        },
        follow_redirects=False,
    )
    assert res.status_code == 302
    assert "/login" in res.headers["Location"]


def test_cannot_delete_without_login(client):
    res = client.post("/servers/1/delete", follow_redirects=False)
    assert res.status_code == 302
    assert "/login" in res.headers["Location"]


def test_add_server_appears_on_dashboard(auth_client):
    res = auth_client.post(
        "/servers",
        data={
            "name": "local-box",
            "host": "127.0.0.1",
            "ssh_port": 22,
            "ssh_username": "demo",
            "auth_type": "password",
            "password": "ssh-secret-xyz",
        },
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert b"local-box" in res.data
    assert b"127.0.0.1" in res.data
    # Credential must not be echoed in HTML
    assert b"ssh-secret-xyz" not in res.data
    for label in (b"CPU", b"Memory", b"Disk", b"Load average", b"Network",
                  b"Listening ports", b"Processes"):
        assert label in res.data


def test_remove_server(auth_client, app):
    auth_client.post(
        "/servers",
        data={
            "name": "temp-box",
            "host": "127.0.0.1",
            "ssh_port": 22,
            "ssh_username": "demo",
            "auth_type": "key",
            "key_path": "/tmp/nonexistent-demo-key",
        },
        follow_redirects=True,
    )
    from app import store

    with app.app_context():
        servers = store.list_servers()
        assert len(servers) == 1
        sid = servers[0]["id"]

    res = auth_client.post(f"/servers/{sid}/delete", follow_redirects=True)
    assert res.status_code == 200
    assert b"temp-box" not in res.data
    assert b"No servers yet" in res.data
