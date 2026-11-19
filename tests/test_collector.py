"""Phase 4 parser / collector unit tests — offline fixtures only."""

from app.collector import (
    build_metrics_dict,
    collect_via_ssh,
    parse_cpu,
    parse_disk,
    parse_load,
    parse_memory,
    parse_network,
    parse_ports,
    parse_processes,
)

SAMPLE_STAT = "cpu  100 0 100 800 0 0 0 0 0 0\ncpu0 50 0 50 400 0 0 0 0 0 0\n"
SAMPLE_MEM = """MemTotal:        8000000 kB
MemFree:         2000000 kB
MemAvailable:    3000000 kB
Buffers:          100000 kB
Cached:           500000 kB
"""
SAMPLE_LOAD = "0.50 0.60 0.70 2/100 1234\n"
SAMPLE_DF = """Filesystem     1K-blocks    Used Available Use% Mounted on
/dev/sda1       10000000 4000000   6000000  40% /
"""
SAMPLE_NET = """Inter-|   Receive                                                |  Transmit
 face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
    lo: 1000 10 0 0 0 0 0 0 1000 10 0 0 0 0 0 0
  eth0: 2000 20 0 0 0 0 0 0 4000 40 0 0 0 0 0 0
"""
SAMPLE_SS = """LISTEN 0 128 0.0.0.0:22 0.0.0.0:* users:(("sshd",pid=1,fd=3))
LISTEN 0 128 127.0.0.1:5000 0.0.0.0:* users:(("python",pid=2,fd=3))
"""
SAMPLE_PS = """  PID %CPU %MEM COMMAND
    1  1.0  0.5 systemd
    2  0.5  0.2 sshd
"""


def test_build_metrics_dict_has_seven_keys():
    data = build_metrics_dict(
        cpu_raw=SAMPLE_STAT,
        mem_raw=SAMPLE_MEM,
        load_raw=SAMPLE_LOAD,
        disk_raw=SAMPLE_DF,
        net_raw=SAMPLE_NET,
        ports_raw=SAMPLE_SS,
        procs_raw=SAMPLE_PS,
    )
    for key in ("cpu", "memory", "disk", "load", "network", "ports", "processes"):
        assert key in data
    assert data["cpu"] == 20.0  # (1000-800)/1000
    assert data["memory"]["percent"] == 62.5
    assert data["load"] == "0.50 / 0.60 / 0.70"
    assert data["disk"]["percent"] == "40%"
    assert data["network"]["rx_bytes"] == 2000
    assert data["network"]["tx_bytes"] == 4000
    assert len(data["ports"]) == 2
    assert len(data["processes"]) == 2
    assert data["error"] is None


def test_parse_cpu_returns_busy_percent():
    assert parse_cpu(SAMPLE_STAT) == 20.0


def test_parse_memory_reports_used_kb():
    assert parse_memory(SAMPLE_MEM)["used_kb"] == 5000000


def test_parse_load_formats_three_intervals():
    assert parse_load(SAMPLE_LOAD) == "0.50 / 0.60 / 0.70"


def test_parse_disk_reports_used_kb():
    assert parse_disk(SAMPLE_DF)["used_kb"] == 4000000


def test_parse_network_skips_loopback():
    assert parse_network(SAMPLE_NET)["rx_bytes"] == 2000


def test_parse_ports_keeps_listener_rows():
    assert "sshd" in parse_ports(SAMPLE_SS)[0]


def test_parse_processes_drops_header():
    procs = parse_processes(SAMPLE_PS)
    assert len(procs) == 2
    assert "systemd" in procs[0]


def test_ssh_unreachable_returns_error_state(monkeypatch):
    """Simulated connection failure; no live SSH."""
    import paramiko

    def fail_connect(self, *args, **kwargs):
        raise OSError("simulated unreachable host")

    monkeypatch.setattr(paramiko.SSHClient, "connect", fail_connect)
    data = collect_via_ssh(
        host="203.0.113.10",  # TEST-NET documentation IP
        port=22,
        username="nobody",
        auth_type="password",
        credential="not-a-real-password",
    )
    assert data["error"] == "unreachable"
    assert data["cpu"] is None
