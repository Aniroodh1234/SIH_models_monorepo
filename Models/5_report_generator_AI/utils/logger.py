

import sys
import io
import time
import functools
from loguru import logger


# ── Fix Windows console encoding ─────────────────────────────────
# Reconfigure stdout/stderr to handle UTF-8 with error replacement
# so emojis and special chars don't crash the logger on Windows (cp1252)
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# ── Configure Loguru ──────────────────────────────────────────────
logger.remove()  # Remove default handler

# Console handler: colorful, concise
logger.add(
    sys.stdout,
    format=(
        "<green>{time:HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<level>{message}</level>"
    ),
    level="WARNING",
    colorize=True,
)

# File handler: detailed, rotated
logger.add(
    "logs/pipeline_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
    level="DEBUG",
    rotation="10 MB",
    retention="7 days",
    compression="zip",
    enqueue=True,
)


def log_step(step_name: str):
    """
    Decorator that logs the start/end/duration of a pipeline step.

    Usage:
        @log_step("Retrieving survey documents")
        def retrieve_survey(category):
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger.info(f">> START -- {step_name}")
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                elapsed = time.perf_counter() - start
                logger.success(f"OK DONE  -- {step_name} ({elapsed:.2f}s)")
                return result
            except Exception as e:
                elapsed = time.perf_counter() - start
                logger.error(f"XX FAIL  -- {step_name} ({elapsed:.2f}s): {e}")
                raise
        return wrapper

    # Support async functions too
    def async_decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            logger.info(f">> START -- {step_name}")
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                elapsed = time.perf_counter() - start
                logger.success(f"OK DONE  -- {step_name} ({elapsed:.2f}s)")
                return result
            except Exception as e:
                elapsed = time.perf_counter() - start
                logger.error(f"XX FAIL  -- {step_name} ({elapsed:.2f}s): {e}")
                raise
        return wrapper

    def smart_decorator(func):
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_decorator(func)
        return decorator(func)

    return smart_decorator


def get_logger(name: str = "report_generator"):
    """Get a contextualized logger."""
    return logger.bind(name=name)
