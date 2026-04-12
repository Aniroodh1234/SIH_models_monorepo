"""
SSE (Server-Sent Events) helpers for streaming responses.

Provides:
  - format_sse()         : Format a Python dict into an SSE wire-format string
  - sync_gen_to_async()  : Bridge a blocking synchronous generator into an async generator
"""

import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Generator, AsyncGenerator

# Shared thread pool for running synchronous generators off the event loop
_stream_executor = ThreadPoolExecutor(max_workers=4)


def format_sse(event: str, data: dict) -> str:
    """
    Format a Server-Sent Event string.

    Args:
        event: SSE event type (e.g. "progress", "token", "complete", "error")
        data:  Dict payload — will be JSON-serialised into the data field

    Returns:
        A correctly formatted SSE string ready to be sent over the wire.
        The trailing double-newline is included (SSE spec requirement).
    """
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def sync_gen_to_async(sync_gen: Generator) -> AsyncGenerator:
    """
    Convert a synchronous (blocking) generator into an async generator.

    Runs the sync generator inside a thread pool executor and bridges
    items to the async world via an asyncio.Queue. This prevents
    the event loop from being blocked by synchronous SDK calls
    (e.g., Gemini streaming).

    Args:
        sync_gen: A synchronous generator that yields items

    Yields:
        Items produced by the synchronous generator, one at a time
    """
    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_event_loop()
    SENTINEL = object()

    def _producer():
        try:
            for item in sync_gen:
                loop.call_soon_threadsafe(queue.put_nowait, item)
        except Exception as exc:
            # Push the exception so the consumer can re-raise it
            loop.call_soon_threadsafe(queue.put_nowait, exc)
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, SENTINEL)

    # Fire-and-forget the producer in a background thread
    loop.run_in_executor(_stream_executor, _producer)

    while True:
        item = await queue.get()
        if item is SENTINEL:
            break
        if isinstance(item, Exception):
            raise item
        yield item
