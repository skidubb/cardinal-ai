"""
API Resilience Layer for Cardinal Element C-Suite.

Provides retry logic, caching, graceful degradation, and structured logging
for all external API calls. Applied to SEC EDGAR, Census Bureau, BLS, and
GitHub clients.

CTO Sprint 2 Deliverable 4: API Rate Limit and Error Resilience Hardening.

Features:
- Exponential backoff retry with jitter
- TTL-based response cache (in-memory for Streamlit, file-based for CLI)
- Circuit breaker pattern for failing APIs
- Graceful degradation: partial results instead of stack traces
- Structured logging for post-mortem debugging

Tech Debt (Named):
- In-memory cache only (no Redis/persistent cache in Sprint 2)
- Circuit breaker thresholds are hardcoded (should be configurable in Sprint 3)
- File-based cache uses JSON serialization (not ideal for large payloads)
"""

import asyncio
import functools
import hashlib
import json
import logging
import os
import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, TypeVar

# ============================================================================
# Structured Logging
# ============================================================================

LOG_DIR = Path(os.environ.get(
    "CSUITE_LOG_DIR",
    Path(__file__).parent.parent.parent.parent / "logs"
))
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Configure structured logger
logger = logging.getLogger("csuite.resilience")
logger.setLevel(logging.DEBUG)

# File handler for structured logs
_file_handler = logging.FileHandler(LOG_DIR / "api_resilience.log")
_file_handler.setLevel(logging.DEBUG)
_file_handler.setFormatter(logging.Formatter(
    "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
))
logger.addHandler(_file_handler)

# Console handler for warnings and above
_console_handler = logging.StreamHandler()
_console_handler.setLevel(logging.WARNING)
_console_handler.setFormatter(logging.Formatter(
    "%(levelname)s: %(message)s"
))
logger.addHandler(_console_handler)


def log_api_call(
    api_name: str,
    endpoint: str,
    status: str,
    duration_ms: float,
    error: str | None = None,
    cached: bool = False,
    retry_count: int = 0,
) -> None:
    """Log a structured API call record."""
    record = {
        "timestamp": datetime.now().isoformat(),
        "api": api_name,
        "endpoint": endpoint,
        "status": status,
        "duration_ms": round(duration_ms, 2),
        "cached": cached,
        "retry_count": retry_count,
    }
    if error:
        record["error"] = error

    log_line = json.dumps(record)

    if status == "success":
        logger.info(log_line)
    elif status == "retry":
        logger.warning(log_line)
    else:
        logger.error(log_line)


# ============================================================================
# Retry with Exponential Backoff
# ============================================================================

T = TypeVar("T")


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 30.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: tuple[type[Exception], ...] = (
        ConnectionError,
        TimeoutError,
        OSError,
    )


# Default retry config for external APIs
DEFAULT_RETRY_CONFIG = RetryConfig(
    max_retries=3,
    base_delay=1.0,
    max_delay=15.0,
)

# More aggressive retry for live demos
DEMO_RETRY_CONFIG = RetryConfig(
    max_retries=5,
    base_delay=0.5,
    max_delay=10.0,
)


def _calculate_delay(attempt: int, config: RetryConfig) -> float:
    """Calculate delay with exponential backoff and optional jitter."""
    delay = min(
        config.base_delay * (config.exponential_base ** attempt),
        config.max_delay,
    )
    if config.jitter:
        delay = delay * (0.5 + random.random() * 0.5)
    return delay


async def retry_async(
    func: Callable[..., Any],
    *args: Any,
    config: RetryConfig | None = None,
    api_name: str = "unknown",
    endpoint: str = "",
    **kwargs: Any,
) -> Any:
    """Execute an async function with retry logic.

    Args:
        func: Async function to call
        config: Retry configuration
        api_name: Name of the API for logging
        endpoint: Endpoint being called for logging

    Returns:
        The function's return value

    Raises:
        The last exception if all retries are exhausted
    """
    config = config or DEFAULT_RETRY_CONFIG
    last_exception = None

    for attempt in range(config.max_retries + 1):
        start_time = time.monotonic()
        try:
            result = await func(*args, **kwargs)
            duration_ms = (time.monotonic() - start_time) * 1000

            log_api_call(
                api_name=api_name,
                endpoint=endpoint,
                status="success",
                duration_ms=duration_ms,
                retry_count=attempt,
            )
            return result

        except config.retryable_exceptions as e:
            duration_ms = (time.monotonic() - start_time) * 1000
            last_exception = e

            if attempt < config.max_retries:
                delay = _calculate_delay(attempt, config)
                log_api_call(
                    api_name=api_name,
                    endpoint=endpoint,
                    status="retry",
                    duration_ms=duration_ms,
                    error=f"{type(e).__name__}: {e}",
                    retry_count=attempt,
                )
                await asyncio.sleep(delay)
            else:
                log_api_call(
                    api_name=api_name,
                    endpoint=endpoint,
                    status="failed",
                    duration_ms=duration_ms,
                    error=f"{type(e).__name__}: {e}",
                    retry_count=attempt,
                )

        except Exception as e:
            duration_ms = (time.monotonic() - start_time) * 1000
            log_api_call(
                api_name=api_name,
                endpoint=endpoint,
                status="error",
                duration_ms=duration_ms,
                error=f"{type(e).__name__}: {e}",
                retry_count=attempt,
            )
            raise

    raise last_exception  # type: ignore[misc]


def with_retry(
    config: RetryConfig | None = None,
    api_name: str = "unknown",
) -> Callable:
    """Decorator to add retry logic to async functions.

    Usage:
        @with_retry(api_name="sec_edgar")
        async def fetch_data(url):
            ...
    """
    config_ = config or DEFAULT_RETRY_CONFIG

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await retry_async(
                func, *args,
                config=config_,
                api_name=api_name,
                endpoint=func.__name__,
                **kwargs,
            )
        return wrapper
    return decorator


# ============================================================================
# TTL Cache
# ============================================================================

@dataclass
class CacheEntry:
    """A single cache entry with TTL."""

    value: Any
    created_at: float
    ttl_seconds: float

    @property
    def is_expired(self) -> bool:
        return (time.monotonic() - self.created_at) > self.ttl_seconds


class TTLCache:
    """In-memory TTL cache for API responses.

    Thread-safe for Streamlit's execution model. Entries expire after
    a configurable TTL. Designed for demo use where the same company
    is researched multiple times -- subsequent lookups are instant.
    """

    def __init__(self, default_ttl: float = 300.0, max_size: int = 500):
        """Initialize cache.

        Args:
            default_ttl: Default time-to-live in seconds (5 minutes)
            max_size: Maximum number of entries before eviction
        """
        self.default_ttl = default_ttl
        self.max_size = max_size
        self._cache: dict[str, CacheEntry] = {}
        self._hits = 0
        self._misses = 0

    def _make_key(self, *args: Any, **kwargs: Any) -> str:
        """Generate a cache key from function arguments."""
        key_data = json.dumps({"args": str(args), "kwargs": str(kwargs)}, sort_keys=True)
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]

    def get(self, key: str) -> Any | None:
        """Get a value from cache. Returns None if missing or expired."""
        entry = self._cache.get(key)
        if entry is None:
            self._misses += 1
            return None
        if entry.is_expired:
            del self._cache[key]
            self._misses += 1
            return None
        self._hits += 1
        return entry.value

    def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        """Set a value in cache with TTL."""
        # Evict expired entries if at capacity
        if len(self._cache) >= self.max_size:
            self._evict_expired()

        # If still at capacity, evict oldest
        if len(self._cache) >= self.max_size:
            oldest_key = min(self._cache, key=lambda k: self._cache[k].created_at)
            del self._cache[oldest_key]

        self._cache[key] = CacheEntry(
            value=value,
            created_at=time.monotonic(),
            ttl_seconds=ttl or self.default_ttl,
        )

    def _evict_expired(self) -> None:
        """Remove all expired entries."""
        expired = [k for k, v in self._cache.items() if v.is_expired]
        for k in expired:
            del self._cache[k]

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    @property
    def stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        total = self._hits + self._misses
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / total if total > 0 else 0,
        }


# Global cache instances
# Short TTL for live data (5 minutes)
api_cache = TTLCache(default_ttl=300.0, max_size=500)

# Long TTL for demo/presentation data (1 hour)
demo_cache = TTLCache(default_ttl=3600.0, max_size=100)


def with_cache(
    cache: TTLCache | None = None,
    ttl: float | None = None,
    key_prefix: str = "",
) -> Callable:
    """Decorator to cache async function results.

    Usage:
        @with_cache(key_prefix="sec_edgar")
        async def get_company_info(ticker):
            ...
    """
    cache_ = cache or api_cache

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            cache_key = f"{key_prefix}:{func.__name__}:{cache_._make_key(*args, **kwargs)}"
            cached = cache_.get(cache_key)
            if cached is not None:
                log_api_call(
                    api_name=key_prefix or "cache",
                    endpoint=func.__name__,
                    status="success",
                    duration_ms=0.0,
                    cached=True,
                )
                return cached

            result = await func(*args, **kwargs)
            if result is not None:
                cache_.set(cache_key, result, ttl=ttl)
            return result
        return wrapper
    return decorator


# ============================================================================
# Circuit Breaker
# ============================================================================

@dataclass
class CircuitBreakerState:
    """State tracking for a circuit breaker."""

    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0.0
    state: str = "closed"  # closed, open, half_open


class CircuitBreaker:
    """Circuit breaker to prevent cascading failures.

    When an API fails repeatedly, the circuit opens and subsequent calls
    fail immediately with a friendly message instead of waiting for timeouts.
    After a cooldown period, the circuit enters half-open state and allows
    a single test request through.

    States:
    - closed: Normal operation, requests pass through
    - open: API is failing, requests fail immediately
    - half_open: Cooldown elapsed, one test request allowed
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 2,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self._breakers: dict[str, CircuitBreakerState] = {}

    def _get_state(self, name: str) -> CircuitBreakerState:
        if name not in self._breakers:
            self._breakers[name] = CircuitBreakerState()
        return self._breakers[name]

    def is_open(self, name: str) -> bool:
        """Check if circuit is open (blocking requests)."""
        state = self._get_state(name)

        if state.state == "open":
            # Check if recovery timeout has elapsed
            if (time.monotonic() - state.last_failure_time) > self.recovery_timeout:
                state.state = "half_open"
                logger.info(f"Circuit breaker '{name}' entering half_open state")
                return False
            return True

        return False

    def record_success(self, name: str) -> None:
        """Record a successful request."""
        state = self._get_state(name)
        state.success_count += 1

        if state.state == "half_open":
            if state.success_count >= self.success_threshold:
                state.state = "closed"
                state.failure_count = 0
                state.success_count = 0
                logger.info(f"Circuit breaker '{name}' closed (recovered)")

    def record_failure(self, name: str) -> None:
        """Record a failed request."""
        state = self._get_state(name)
        state.failure_count += 1
        state.last_failure_time = time.monotonic()

        if state.failure_count >= self.failure_threshold:
            state.state = "open"
            logger.warning(
                f"Circuit breaker '{name}' opened after {state.failure_count} failures"
            )

    def get_status(self) -> dict[str, str]:
        """Get status of all circuit breakers."""
        return {name: state.state for name, state in self._breakers.items()}


# Global circuit breaker
circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60.0,
    success_threshold=2,
)


# ============================================================================
# Graceful Degradation
# ============================================================================

@dataclass
class DegradedResult:
    """A result that indicates partial or degraded data.

    Used when an API call fails but we can still return something useful.
    The demo UI checks for this type and displays an appropriate message.
    """

    data: Any = None
    is_degraded: bool = True
    error_message: str = ""
    api_name: str = ""
    suggestion: str = "Try again in a few moments."

    def __bool__(self) -> bool:
        """Allow truthiness check -- degraded results are still truthy if they have data."""
        return self.data is not None


def graceful_fallback(
    api_name: str,
    default_value: Any = None,
    message: str = "",
) -> Callable:
    """Decorator for graceful degradation on API failures.

    Instead of raising an exception, returns a DegradedResult with
    the error message and a default value. The UI layer can then
    display partial results with a note about what failed.

    Usage:
        @graceful_fallback(api_name="SEC EDGAR", default_value=None)
        async def get_company_info(ticker):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error_msg = message or f"{api_name} is temporarily unavailable: {type(e).__name__}"
                logger.warning(f"Graceful fallback for {api_name}.{func.__name__}: {e}")
                return DegradedResult(
                    data=default_value,
                    error_message=error_msg,
                    api_name=api_name,
                    suggestion=f"The {api_name} API may be experiencing issues. "
                               "Cached data will be used when available.",
                )
        return wrapper
    return decorator


# ============================================================================
# Convenience: Combined Resilience Decorator
# ============================================================================

def resilient(
    api_name: str,
    retry_config: RetryConfig | None = None,
    cache_ttl: float | None = None,
    default_value: Any = None,
) -> Callable:
    """Combined decorator applying retry + cache + graceful degradation.

    This is the standard decorator for all external API calls in the
    C-Suite application. It layers:
    1. Cache check (instant return if cached)
    2. Retry with exponential backoff
    3. Graceful fallback on exhausted retries

    Usage:
        @resilient(api_name="sec_edgar", cache_ttl=300)
        async def get_company_info(ticker):
            ...
    """
    retry_cfg = retry_config or DEFAULT_RETRY_CONFIG

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # 1. Check cache
            cache_key = f"{api_name}:{func.__name__}:{api_cache._make_key(*args, **kwargs)}"
            cached = api_cache.get(cache_key)
            if cached is not None:
                log_api_call(
                    api_name=api_name,
                    endpoint=func.__name__,
                    status="success",
                    duration_ms=0.0,
                    cached=True,
                )
                return cached

            # 2. Check circuit breaker
            if circuit_breaker.is_open(api_name):
                logger.warning(f"Circuit open for {api_name}, returning degraded result")
                return DegradedResult(
                    data=default_value,
                    error_message=f"{api_name} is temporarily unavailable (circuit open).",
                    api_name=api_name,
                    suggestion=(
                        "The API has been failing recently."
                        " It will be retried automatically."
                    ),
                )

            # 3. Retry with backoff
            try:
                result = await retry_async(
                    func, *args,
                    config=retry_cfg,
                    api_name=api_name,
                    endpoint=func.__name__,
                    **kwargs,
                )

                # Cache successful result
                if result is not None and cache_ttl:
                    api_cache.set(cache_key, result, ttl=cache_ttl)

                circuit_breaker.record_success(api_name)
                return result

            except Exception as e:
                circuit_breaker.record_failure(api_name)
                error_msg = f"{api_name} unavailable: {type(e).__name__}"
                logger.error(f"All retries exhausted for {api_name}.{func.__name__}: {e}")
                return DegradedResult(
                    data=default_value,
                    error_message=error_msg,
                    api_name=api_name,
                    suggestion=f"The {api_name} API is not responding. "
                               "Try again in a minute.",
                )

        return wrapper
    return decorator
