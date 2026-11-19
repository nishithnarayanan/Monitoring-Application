"""Read-only host metrics: local commands or agentless SSH (Paramiko)."""

from __future__ import annotations

import logging
import re
import socket
import subprocess
from typing import Any

logger = logging.getLogger(__name__)

# Fixed command strings only — never interpolate user-controlled host/input into a shell.
CMD_CPU = "grep 'cpu ' /proc/stat"
CMD_MEM = "cat /proc/meminfo"
CMD_LOAD = "cat /proc/loadavg"
CMD_DISK = "df -k /"
CMD_NET = "cat /proc/net/dev"
CMD_PORTS = "ss -lptunH 2>/dev/null || netstat -lptun 2>/dev/null || true"
CMD_PROCS = "ps -eo pid,pcpu,pmem,comm --sort=-pcpu | head -n 6"

COLLECT_TIMEOUT = 8


def is_local_host(host: str) -> bool:
    h = (host or "").strip().lower()
    return h in {"127.0.0.1", "localhost", "::1"}


def parse_cpu(stat_text: str) -> float | None:
    for line in stat_text.splitlines():
        if line.startswith("cpu "):
            parts = line.split()
            if len(parts) < 5:
                return None
            nums = [int(x) for x in parts[1:]]
            idle = nums[3] + (nums[4] if len(nums) > 4 else 0)
            total = sum(nums)
            if total <= 0:
                return None
            return round(100.0 * (1.0 - idle / total), 1)
    return None


def parse_memory(meminfo: str) -> dict[str, Any] | None:
    vals: dict[str, int] = {}
    for line in meminfo.splitlines():
        m = re.match(r"^(\w+):\s+(\d+)", line)
        if m:
            vals[m.group(1)] = int(m.group(2))
    total = vals.get("MemTotal")
    available = vals.get("MemAvailable")
    if total is None:
        return None
    if available is None:
        free = vals.get("MemFree", 0)
        buffers = vals.get("Buffers", 0)
        cached = vals.get("Cached", 0)
        available = free + buffers + cached
    used = max(total - available, 0)
    return {
        "total_kb": total,
        "used_kb": used,
        "free_kb": available,
        "percent": round(100.0 * used / total, 1) if total else None,
    }


def parse_load(loadavg: str) -> str | None:
    parts = loadavg.strip().split()
    if len(parts) < 3:
        return None
    return f"{parts[0]} / {parts[1]} / {parts[2]}"


def parse_disk(df_text: str) -> dict[str, Any] | None:
    lines = [ln for ln in df_text.strip().splitlines() if ln.strip()]
    if len(lines) < 2:
        return None
    # Handle wrapped df headers: take last line with enough fields.
    fields = lines[-1].split()
    if len(fields) < 5:
        return None
    try:
        total_k, used_k, avail_k = int(fields[1]), int(fields[2]), int(fields[3])
        pct = fields[4]
    except ValueError:
        return None
    return {
        "total_kb": total_k,
        "used_kb": used_k,
        "avail_kb": avail_k,
        "percent": pct,
    }


def parse_network(netdev: str) -> dict[str, int] | None:
    rx = tx = 0
    for line in netdev.splitlines():
        if ":" not in line:
            continue
        name, rest = line.split(":", 1)
        iface = name.strip()
        if iface == "lo":
            continue
        cols = rest.split()
        if len(cols) < 9:
            continue
        try:
            rx += int(cols[0])
            tx += int(cols[8])
        except ValueError:
            continue
    return {"rx_bytes": rx, "tx_bytes": tx}


def parse_ports(ss_text: str) -> list[str]:
    rows: list[str] = []
    for line in ss_text.splitlines():
        line = line.strip()
        if not line or line.lower().startswith("netid") or line.lower().startswith("proto"):
            continue
        rows.append(line)
        if len(rows) >= 12:
            break
    return rows


def parse_processes(ps_text: str) -> list[str]:
    lines = [ln.rstrip() for ln in ps_text.splitlines() if ln.strip()]
    # Drop header if present.
    if lines and lines[0].lower().lstrip().startswith("pid"):
        lines = lines[1:]
    return lines[:5]


def build_metrics_dict(
    *,
    cpu_raw: str,
    mem_raw: str,
    load_raw: str,
    disk_raw: str,
    net_raw: str,
    ports_raw: str,
    procs_raw: str,
) -> dict[str, Any]:
    cpu = parse_cpu(cpu_raw)
    mem = parse_memory(mem_raw)
    load = parse_load(load_raw)
    disk = parse_disk(disk_raw)
    net = parse_network(net_raw)
    ports = parse_ports(ports_raw)
    procs = parse_processes(procs_raw)
    return {
        "cpu": cpu,
        "memory": mem,
        "disk": disk,
        "load": load,
        "network": net,
        "ports": ports,
        "processes": procs,
        "error": None,
    }


def _unreachable() -> dict[str, Any]:
    """Metrics dict shown when a host cannot be collected from."""
    return {
        "error": "unreachable",
        "cpu": None,
        "memory": None,
        "disk": None,
        "load": None,
        "network": None,
        "ports": [],
        "processes": [],
    }


def _run_local(cmd: str) -> str:
    result = subprocess.run(
        ["bash", "-c", cmd],
        capture_output=True,
        text=True,
        timeout=COLLECT_TIMEOUT,
        check=False,
    )
    return result.stdout or ""


def collect_local() -> dict[str, Any]:
    try:
        return build_metrics_dict(
            cpu_raw=_run_local(CMD_CPU),
            mem_raw=_run_local(CMD_MEM),
            load_raw=_run_local(CMD_LOAD),
            disk_raw=_run_local(CMD_DISK),
            net_raw=_run_local(CMD_NET),
            ports_raw=_run_local(CMD_PORTS),
            procs_raw=_run_local(CMD_PROCS),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.info("Local collect failed: %s", type(exc).__name__)
        return _unreachable()


def _ssh_run(client, cmd: str) -> str:
    _stdin, stdout, _stderr = client.exec_command(cmd, timeout=COLLECT_TIMEOUT)
    return stdout.read().decode("utf-8", errors="replace")


def collect_via_ssh(
    *,
    host: str,
    port: int,
    username: str,
    auth_type: str,
    credential: str,
) -> dict[str, Any]:
    import paramiko

    client = paramiko.SSHClient()
    # Verify against known host keys; unknown hosts are rejected (no AutoAddPolicy).
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    try:
        kwargs: dict[str, Any] = {
            "hostname": host,
            "port": int(port),
            "username": username,
            "timeout": COLLECT_TIMEOUT,
            "allow_agent": False,
            "look_for_keys": False,
        }
        if auth_type == "password":
            kwargs["password"] = credential
        else:
            kwargs["key_filename"] = credential
        client.connect(**kwargs)
        data = build_metrics_dict(
            cpu_raw=_ssh_run(client, CMD_CPU),
            mem_raw=_ssh_run(client, CMD_MEM),
            load_raw=_ssh_run(client, CMD_LOAD),
            disk_raw=_ssh_run(client, CMD_DISK),
            net_raw=_ssh_run(client, CMD_NET),
            ports_raw=_ssh_run(client, CMD_PORTS),
            procs_raw=_ssh_run(client, CMD_PROCS),
        )
        return data
    except (OSError, EOFError, paramiko.SSHException) as exc:
        logger.info("SSH collect failed for host=%s: %s", host, type(exc).__name__)
        return _unreachable()
    finally:
        try:
            client.close()
        except (OSError, paramiko.SSHException):
            logger.debug("SSH client close failed (non-fatal)")


def check_connectivity(
    *,
    host: str,
    port: int,
    username: str,
    auth_type: str,
    credential: str,
) -> bool:
    """Return True if host looks reachable (local always true; else TCP/SSH)."""
    if is_local_host(host):
        return True
    try:
        with socket.create_connection((host, int(port)), timeout=3):
            pass
    except OSError:
        return False
    # Optional deeper SSH check — failure still counts as unreachable.
    result = collect_via_ssh(
        host=host,
        port=port,
        username=username,
        auth_type=auth_type,
        credential=credential,
    )
    return result.get("error") is None


def collect_for_server(server: dict[str, Any]) -> dict[str, Any]:
    """`server` must include secrets when remote (from store.get_server include_secret)."""
    host = server["host"]
    if is_local_host(host):
        return collect_local()
    return collect_via_ssh(
        host=host,
        port=int(server.get("ssh_port") or 22),
        username=server["ssh_username"],
        auth_type=server["auth_type"],
        credential=server.get("credential") or "",
    )
