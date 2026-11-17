"""Host Monitor metric panels — placeholders or live collector data."""

from __future__ import annotations

from typing import Any

# Display order matches the Host Monitor snip.
METRIC_PANELS = [
    {"key": "cpu", "title": "CPU", "subtitle": "Overall usage %"},
    {"key": "memory", "title": "Memory", "subtitle": "Used / free"},
    {"key": "disk", "title": "Disk", "subtitle": "Root filesystem"},
    {"key": "load", "title": "Load average", "subtitle": "1 / 5 / 15 min"},
    {"key": "network", "title": "Network", "subtitle": "RX / TX"},
    {"key": "ports", "title": "Listening ports", "subtitle": "TCP / UDP"},
    {"key": "processes", "title": "Processes", "subtitle": "Top by CPU / memory"},
]


def _fmt_bytes(n: int) -> str:
    for unit, div in (("GB", 1024**3), ("MB", 1024**2), ("KB", 1024)):
        if n >= div:
            return f"{n / div:.1f} {unit}"
    return f"{n} B"


def _fmt_kb(kb: int) -> str:
    return _fmt_bytes(kb * 1024)


def placeholder_metrics() -> list[dict]:
    """Return UI-ready panels with no live values yet."""
    return [
        {
            **panel,
            "value": None,
            "display": "No data yet",
            "lines": None,
        }
        for panel in METRIC_PANELS
    ]


def panels_from_data(data: dict[str, Any] | None) -> list[dict]:
    """Map collector output into the seven Host Monitor cards."""
    if not data or data.get("error"):
        panels = placeholder_metrics()
        if data and data.get("error"):
            for p in panels:
                p["display"] = "Unreachable"
        return panels

    out: list[dict] = []
    for panel in METRIC_PANELS:
        key = panel["key"]
        value: Any = data.get(key)
        lines = None
        display = "No data yet"

        if key == "cpu" and value is not None:
            display = f"{value}%"
        elif key == "memory" and isinstance(value, dict):
            display = (
                f"{_fmt_kb(value['used_kb'])} used / "
                f"{_fmt_kb(value['free_kb'])} free"
                + (f" ({value['percent']}%)" if value.get("percent") is not None else "")
            )
        elif key == "disk" and isinstance(value, dict):
            display = (
                f"{_fmt_kb(value['used_kb'])} / {_fmt_kb(value['total_kb'])} "
                f"({value.get('percent', '?')})"
            )
        elif key == "load" and value:
            display = str(value)
        elif key == "network" and isinstance(value, dict):
            display = (
                f"RX {_fmt_bytes(value['rx_bytes'])} · "
                f"TX {_fmt_bytes(value['tx_bytes'])}"
            )
        elif key == "ports":
            lines = value or []
            display = f"{len(lines)} listening" if lines else "No data yet"
        elif key == "processes":
            lines = value or []
            display = "Top processes" if lines else "No data yet"

        out.append(
            {
                **panel,
                "value": value,
                "display": display,
                "lines": lines,
            }
        )
    return out
