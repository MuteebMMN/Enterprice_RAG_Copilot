"""Simple in-memory rate limits for /api/chat so a public demo cannot run up the API bill.

Two limits: per client IP (short window, stops one visitor hammering) and per user account
(daily, a global cap for the shared demo account). State resets when the app restarts.
"""
import time
from collections import defaultdict, deque
from fastapi import Depends, HTTPException, Request
from app.core.config import get_settings
from app.core.deps import CurrentUser, get_current_user

IP_WINDOW_SECONDS = 600
USER_WINDOW_SECONDS = 86400


class SlidingWindow:
    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window = window_seconds
        self.hits: dict[str, deque] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        q = self.hits[key]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        return True


_settings = get_settings()
_per_ip = SlidingWindow(_settings.chat_rate_per_ip, IP_WINDOW_SECONDS)
_per_user = SlidingWindow(_settings.chat_rate_per_user, USER_WINDOW_SECONDS)


def chat_rate_limit(request: Request, user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    ip = request.client.host if request.client else "unknown"
    if not _per_ip.allow(ip):
        raise HTTPException(status_code=429, detail="You're sending questions too fast. Please wait a few minutes and try again.")
    if not _per_user.allow(str(user.id)):
        raise HTTPException(status_code=429, detail="This account has reached its daily question limit. Please try again tomorrow.")
    return user
