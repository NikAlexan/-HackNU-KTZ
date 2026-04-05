"""
In-memory live state for all locomotives.

- _latest: most recent packet per loco_id (for instant WS delivery on connect)
- _accumulator: packets collected in the current 60s window (for aggregate write)
- _loco_clients: per-loco WebSocket subscribers notified on every new packet
"""
from collections import defaultdict

from fastapi import WebSocket

_latest: dict[str, dict] = {}
_accumulator: dict[str, list] = defaultdict(list)
_loco_clients: dict[str, set[WebSocket]] = defaultdict(set)


def push(packet: dict) -> None:
    loco_id = packet.get("loco_id")
    if not loco_id:
        return
    _latest[loco_id] = packet
    _accumulator[loco_id].append(packet)


def get(loco_id: str) -> dict | None:
    return _latest.get(loco_id)


def get_all() -> dict[str, dict]:
    return dict(_latest)


def flush_accumulator(loco_id: str) -> list:
    """Return accumulated packets for the period and clear the buffer."""
    return _accumulator.pop(loco_id, [])


def all_loco_ids() -> list[str]:
    return list(_latest.keys())


def add_client(loco_id: str, ws: WebSocket) -> None:
    _loco_clients[loco_id].add(ws)


def remove_client(loco_id: str, ws: WebSocket) -> None:
    _loco_clients[loco_id].discard(ws)


def notify_clients(loco_id: str) -> set[WebSocket]:
    """Return the client set for sending; caller handles dead-client cleanup."""
    return _loco_clients.get(loco_id, set())
