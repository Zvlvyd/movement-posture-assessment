"""
Simple in-memory rate limiter for authentication endpoints.

Each IP gets a configurable number of attempts per time window.
Exceeding the limit returns HTTP 429.

NOTE: This is intentionally single-process / in-memory.
For multi-process deployments, replace with Redis-backed rate limiting.
"""
import time
import threading
from collections import defaultdict
from fastapi import Request
from fastapi.responses import JSONResponse


class RateLimiter:
    """Per-IP sliding-window rate limiter."""

    def __init__(self, max_requests: int = 5, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._attempts: defaultdict[str, list] = defaultdict(list)
        self._lock = threading.Lock()

    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        with self._lock:
            window_start = now - self.window_seconds
            # Prune expired entries
            self._attempts[client_ip] = [
                ts for ts in self._attempts[client_ip] if ts > window_start
            ]
            if len(self._attempts[client_ip]) >= self.max_requests:
                return False
            self._attempts[client_ip].append(now)
            return True

    def remaining(self, client_ip: str) -> int:
        now = time.time()
        with self._lock:
            window_start = now - self.window_seconds
            self._attempts[client_ip] = [
                ts for ts in self._attempts[client_ip] if ts > window_start
            ]
            return max(0, self.max_requests - len(self._attempts[client_ip]))


# Default instance: 5 attempts per minute per IP for auth endpoints
auth_rate_limiter = RateLimiter(max_requests=5, window_seconds=60)


async def auth_rate_limit_middleware(request: Request, call_next):
    """FastAPI middleware: rate-limit /api/auth/login and /api/auth/register."""
    path = request.url.path.rstrip("/")
    if path not in ("/api/auth/login", "/api/auth/register"):
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    if not auth_rate_limiter.is_allowed(client_ip):
        return JSONResponse(
            status_code=429,
            content={"detail": "请求过于频繁，请稍后再试 (Too Many Requests)"},
        )

    # Only count failed attempts — intercept response to check status
    response = await call_next(request)
    return response
