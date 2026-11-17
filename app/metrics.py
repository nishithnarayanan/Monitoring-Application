"""Placeholder metric panels for the dashboard UI (live data in later phases)."""

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


def placeholder_metrics() -> list[dict]:
    """Return UI-ready panels with no live values yet."""
    return [
        {
            **panel,
            "value": None,
            "display": "No data yet",
        }
        for panel in METRIC_PANELS
    ]
