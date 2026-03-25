# backend/utils/progress_bus.py
"""Thread-safe bridge: sync analysis workers → asyncio WebSocket broadcast."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

_loop: Optional[asyncio.AbstractEventLoop] = None
_queue: Optional[asyncio.Queue] = None


def configure(loop: asyncio.AbstractEventLoop, queue: asyncio.Queue) -> None:
    global _loop, _queue
    _loop = loop
    _queue = queue


def reset() -> None:
    global _loop, _queue
    _loop = None
    _queue = None


def emit_progress(event: Dict[str, Any]) -> None:
    """Safe to call from worker threads (e.g. asyncio.to_thread analysis)."""
    if _loop is None or _queue is None:
        return

    def _put() -> None:
        try:
            _queue.put_nowait(event)
        except asyncio.QueueFull:
            pass

    try:
        _loop.call_soon_threadsafe(_put)
    except RuntimeError:
        pass
