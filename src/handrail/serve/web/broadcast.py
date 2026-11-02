"""The lobby speaker: whatever the stage manager says, everyone listening hears.

A station announcer reads each line of the prompt book into a microphone and
the speakers in every room carry it, none of them holding up the show if a
room is slow to listen. ``Broadcast`` is the microphone; ``WebRecorder`` is
the prompt book that reads itself aloud, masked exactly as written.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from ...kernel.evidence import Recorder

QUEUE_LIMIT = 200


class Broadcast:
    def __init__(self) -> None:
        self._queues: set[asyncio.Queue[dict[str, Any]]] = set()

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._queues.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[dict[str, Any]]) -> None:
        self._queues.discard(q)

    def publish(self, message: dict[str, Any]) -> None:
        for q in list(self._queues):
            if q.qsize() < QUEUE_LIMIT:
                q.put_nowait(message)


class WebRecorder(Recorder):
    """The prompt book that reads each line aloud, masked exactly as it was written."""

    def __init__(
        self,
        *args: Any,
        broadcast: Broadcast,
        on_event: Callable[[dict[str, Any]], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.broadcast = broadcast
        self.on_event = on_event

    def log(self, event: str, **fields: Any) -> None:
        super().log(event, **fields)
        message = {
            "seq": self._seq,
            "at": datetime.now(UTC).isoformat(),
            "event": event,
            **self._mask_value(fields),
            "type": "event",
        }
        if self.on_event is not None:
            self.on_event(message)
        self.broadcast.publish(message)
