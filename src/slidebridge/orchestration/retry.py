"""Tenacity retry wrappers for pipeline stages that call external processes.

Usage
-----
    from slidebridge.orchestration.retry import with_retry, RetryConfig

    @with_retry()
    def my_flaky_call(): ...

    # Or with custom settings:
    @with_retry(RetryConfig(attempts=5, wait_seconds=3))
    def my_call(): ...
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


@dataclass
class RetryConfig:
    """Configuration for retry behaviour."""

    attempts: int = 3
    wait_seconds: float = 2.0
    retry_on: type[Exception] | tuple[type[Exception], ...] = RuntimeError


def with_retry(config: RetryConfig | None = None) -> Callable[[F], F]:
    """Decorator factory that wraps a callable with tenacity retry logic.

    Parameters
    ----------
    config:
        Retry settings.  Defaults to 3 attempts, 2-second fixed wait,
        retrying on ``RuntimeError``.

    Examples
    --------
    >>> @with_retry()
    ... def convert(): ...

    >>> @with_retry(RetryConfig(attempts=5, wait_seconds=1))
    ... def render(): ...
    """
    cfg = config or RetryConfig()

    def decorator(fn: F) -> F:
        wrapped = retry(
            stop=stop_after_attempt(cfg.attempts),
            wait=wait_fixed(cfg.wait_seconds),
            retry=retry_if_exception_type(cfg.retry_on),
            before_sleep=_log_retry,
            reraise=True,
        )(fn)
        return wrapped

    return decorator


def _log_retry(retry_state: Any) -> None:
    """Log each retry attempt at WARNING level."""
    attempt = retry_state.attempt_number
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    logger.warning(
        "Retrying %s (attempt %d): %s",
        getattr(retry_state.fn, "__name__", "unknown"),
        attempt,
        exc,
    )
