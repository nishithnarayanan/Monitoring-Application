"""Phase 0 smoke tests: Host Monitor dashboard UI shell (auth + store)."""

from app import store


def test_dashboard_ok(auth_client, app):
    with app.app_context():
        store.add_server(
            name="demo-web-01",
            host="127.0.0.1",
            ssh_username="monitor",
            auth_type="key",
            key_path="/tmp/demo-key",
        )
    res = auth_client.get("/")
    assert res.status_code == 200
    assert b"Host Monitor" in res.data
    assert b"Monitoring dashboard" in res.data
    assert b"demo-web-01" in res.data
    # Metric panels from the snip (placeholders until later phases)
    for label in (
        b"CPU",
        b"Memory",
        b"Disk",
        b"Load average",
        b"Network",
        b"Listening ports",
        b"Processes",
        b"No data yet",
    ):
        assert label in res.data


def test_dashboard_empty_servers_copy(auth_client):
    res = auth_client.get("/")
    assert res.status_code == 200
    assert b"No servers yet" in res.data
    assert b"Servers" in res.data


def test_server_detail_ok(auth_client, app):
    with app.app_context():
        server = store.add_server(
            name="demo-web-01",
            host="127.0.0.1",
            ssh_username="monitor",
            auth_type="key",
            key_path="/tmp/demo-key",
        )
    res = auth_client.get(f"/servers/{server['id']}")
    assert res.status_code == 200
    assert b"demo-web-01" in res.data
    assert b"CPU" in res.data
    assert b"Disk" in res.data
    assert b"Processes" in res.data


def test_server_detail_not_found(auth_client):
    res = auth_client.get("/servers/999")
    assert res.status_code == 404
    assert b"not found" in res.data.lower()
