"""
Retry and timeout utilities for resilient LLM and API calls.

Usage:
    from src.utils.retry import with_retry, call_with_timeout

    # Decorator — wrap any function that makes an LLM or API call
    @with_retry(max_attempts=3, base_delay=2.0)
    def my_llm_call():
        ...

    # One-shot timeout — runs callable in a thread, raises TimeoutError if exceeded
    result = call_with_timeout(my_function, args=(arg1,), timeout_seconds=90)
"""

import time
import functools
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Callable, Any, Optional

logger = logging.getLogger(__name__)


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 2.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
):
    """
    Decorator that retries a function with exponential backoff.

    Args:
        max_attempts:   Total number of attempts (1 = no retry)
        base_delay:     Seconds to wait after first failure
        backoff_factor: Multiply delay by this on each subsequent failure
        exceptions:     Exception types that trigger a retry

    Delays: 2s → 4s → 8s (with defaults)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = base_delay
            last_exc: Optional[Exception] = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt == max_attempts:
                        logger.warning(
                            "[Retry] %s — all %d attempts failed. Last error: %s",
                            func.__name__, max_attempts, exc,
                        )
                        raise
                    logger.warning(
                        "[Retry] %s — attempt %d/%d failed (%s). Retrying in %.0fs...",
                        func.__name__, attempt, max_attempts, exc, delay,
                    )
                    time.sleep(delay)
                    delay *= backoff_factor

            raise last_exc  # unreachable but satisfies type checkers

        return wrapper
    return decorator


def call_with_timeout(
    func: Callable,
    args: tuple = (),
    kwargs: dict = None,
    timeout_seconds: float = 120,
    label: str = "",
) -> Any:
    """
    Run func(*args, **kwargs) in a thread; raise TimeoutError if it exceeds timeout_seconds.

    Args:
        func:            The callable to run
        args:            Positional arguments for func
        kwargs:          Keyword arguments for func
        timeout_seconds: Hard ceiling in seconds
        label:           Identifier for logging (e.g. NCT ID or agent name)

    Raises:
        TimeoutError: if the call does not complete within timeout_seconds
        Any exception raised by func itself
    """
    if kwargs is None:
        kwargs = {}

    tag = f"[{label}] " if label else ""

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func, *args, **kwargs)
        try:
            return future.result(timeout=timeout_seconds)
        except FuturesTimeoutError:
            msg = f"{tag}Timed out after {timeout_seconds}s"
            logger.error("[Timeout] %s", msg)
            raise TimeoutError(msg)
