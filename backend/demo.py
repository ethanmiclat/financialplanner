"""Demo mode: a public copy of the app that can't touch anyone's real plan.

With FP_DEMO=1 every visitor gets a private profile of their own — the seed student,
in a file keyed by a random id (an X-Footing-Visitor header from a frontend on
another domain, otherwise a cookie) — so they can log updates, change settings and
reset without seeing or affecting anyone else. Files expire after a day and the
total is capped, so a public URL can't fill a disk. The owner's real profile
(FP_STORE) is never read in demo mode.
"""

from __future__ import annotations

import os
import re
import tempfile
import time
import uuid
from pathlib import Path

COOKIE = "footing_demo"
HEADER = "X-Footing-Visitor"
TTL_SECONDS = 24 * 3600
MAX_VISITORS = 500
_ID = re.compile(r"^[0-9a-f]{32}$")


def enabled() -> bool:
    return os.environ.get("FP_DEMO") == "1"


def directory() -> Path:
    return Path(os.environ.get("FP_DEMO_DIR") or Path(tempfile.gettempdir()) / "footing-demo")


def visitor_id(cookie: str | None) -> tuple[str, bool]:
    """The visitor's id and whether it's new. Anything that isn't one of our ids —
    including a path-traversal attempt — just gets a fresh one. A well-formed id with
    no file yet is kept: the page hands out the cookie before the first API call, and
    that call is what creates the sandbox."""
    if cookie and _ID.match(cookie):
        return cookie, False
    return uuid.uuid4().hex, True


def path_for(vid: str) -> Path:
    assert _ID.match(vid)
    return directory() / f"{vid}.json"


def sweep(now: float | None = None) -> int:
    """Drop expired visitors, then the oldest past the cap. Returns how many went."""
    d = directory()
    if not d.exists():
        return 0
    now = now or time.time()
    files = sorted(d.glob("*.json"), key=lambda p: p.stat().st_mtime)
    gone = 0
    for p in files:
        if now - p.stat().st_mtime > TTL_SECONDS:
            p.unlink(missing_ok=True)
            gone += 1
    files = [p for p in files if p.exists()]
    for p in files[: max(0, len(files) - MAX_VISITORS)]:
        p.unlink(missing_ok=True)
        gone += 1
    return gone
