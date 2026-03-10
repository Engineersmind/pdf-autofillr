# chatbot/limits/rate_limiter.py
"""Per-user and per-SDK-key rate limiting."""
from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from threading import Lock
from typing import Optional


@dataclass
class RateLimitConfig:
    messages_per_session: int = 100
    sessions_per_user_per_day: int = 5
    sessions_per_sdk_key_per_day: int = 1000
    llm_calls_per_session: int = 20


class RateLimitExceeded(Exception):
    def __init__(self, message: str, limit_type: str):
        super().__init__(message)
        self.limit_type = limit_type


class RateLimiter:
    """
    In-memory (local) or Redis-backed rate limiter.

    Args:
        config:    Limit thresholds.
        backend:   'local' (default) or 'redis'.
        redis_url: Required when backend='redis'.
    """

    def __init__(
        self,
        config: Optional[RateLimitConfig] = None,
        backend: str = "local",
        redis_url: Optional[str] = None,
    ):
        self.config = config or RateLimitConfig()
        self.backend = backend
        self._lock = Lock()

        if backend == "redis":
            try:
                import redis
                self._redis = redis.from_url(redis_url or "redis://localhost:6379")
            except ImportError:
                raise ImportError("redis package required: pip install chatbot-sdk[redis]")
        else:
            # Local in-memory counters
            self._session_turns: dict = defaultdict(int)         # session_id → count
            self._user_sessions: dict = defaultdict(dict)        # user_id → {date: count}
            self._llm_calls: dict = defaultdict(int)             # session_id → count

    def check(self, user_id: str, session_id: str) -> None:
        """Raise RateLimitExceeded if any limit is breached."""
        if self.backend == "local":
            self._check_local(user_id, session_id)
        else:
            self._check_redis(user_id, session_id)

    def increment_message(self, session_id: str) -> None:
        if self.backend == "local":
            with self._lock:
                self._session_turns[session_id] += 1

    def increment_llm(self, session_id: str) -> None:
        if self.backend == "local":
            with self._lock:
                self._llm_calls[session_id] += 1

    # ------------------------------------------------------------------

    def _check_local(self, user_id: str, session_id: str) -> None:
        with self._lock:
            today = str(date.today())

            # messages_per_session
            if self._session_turns[session_id] >= self.config.messages_per_session:
                raise RateLimitExceeded(
                    f"Session message limit reached ({self.config.messages_per_session}).",
                    limit_type="messages_per_session",
                )

            # sessions_per_user_per_day
            user_today = self._user_sessions[user_id].get(today, 0)
            if session_id not in self._session_turns and user_today >= self.config.sessions_per_user_per_day:
                raise RateLimitExceeded(
                    f"Daily session limit reached ({self.config.sessions_per_user_per_day} per user).",
                    limit_type="sessions_per_user_per_day",
                )

            # Track new session
            if session_id not in self._session_turns:
                self._user_sessions[user_id][today] = user_today + 1

            # llm_calls_per_session
            if self._llm_calls[session_id] >= self.config.llm_calls_per_session:
                raise RateLimitExceeded(
                    f"LLM call limit reached ({self.config.llm_calls_per_session} per session).",
                    limit_type="llm_calls_per_session",
                )

    def _check_redis(self, user_id: str, session_id: str) -> None:
        # Redis implementation — uses atomic INCR with TTL
        today = str(date.today())
        key = f"chatbot:sessions:{user_id}:{today}"
        count = self._redis.incr(key)
        if count == 1:
            self._redis.expire(key, 86400)
        if count > self.config.sessions_per_user_per_day:
            raise RateLimitExceeded(
                f"Daily session limit reached.",
                limit_type="sessions_per_user_per_day",
            )
