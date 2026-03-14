"""In-memory tick store and SSE streaming for the web dashboard.

TickStore accumulates ingested tick data and pushes it to connected
SSE clients via asyncio.Event notification. Clients receive full
history on connect, then incremental updates.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncGenerator


class TickStore:
    """In-memory ring buffer for tick events with SSE push notification."""

    def __init__(self, max_size: int = 500) -> None:
        self._ticks: list[dict[str, Any]] = []
        self._max_size = max_size
        self._event = asyncio.Event()

    @property
    def ticks(self) -> list[dict[str, Any]]:
        """Return all stored ticks."""
        return list(self._ticks)

    def ingest(self, data: dict[str, Any]) -> None:
        """Append a tick and notify SSE listeners."""
        if len(self._ticks) >= self._max_size:
            self._ticks.pop(0)
        self._ticks.append(data)
        self._event.set()
        self._event.clear()

    async def stream(self) -> AsyncGenerator[str, None]:
        """Yield SSE events: full history on connect, then incremental."""
        sent = 0

        for tick in self._ticks:
            yield f"data: {json.dumps(tick)}\n\n"
            sent += 1

        while True:
            await self._event.wait()
            for tick in self._ticks[sent:]:
                yield f"data: {json.dumps(tick)}\n\n"
                sent += 1
