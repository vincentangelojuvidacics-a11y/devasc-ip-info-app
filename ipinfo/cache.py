"""
cache.py - Local cache for online IP lookups (Project Activity 4, backlog #8).

ipapi.co allows about 1,000 free requests per day, and a single bulk lookup
file could use that up. So every SUCCESSFUL lookup is saved in a small JSON
file and reused for 24 hours:

    .cache/lookups.json
    {
      "8.8.8.8": {"saved_at": 1763540000.0, "data": {...normalized details...}}
    }

- Failed lookups are never cached (api.py only calls put() on success).
- A missing or damaged cache file is treated as empty, never as an error.
- The folder can be changed with the IPINFO_CACHE_DIR environment variable
  (the tests and the CI pipeline point it at a temporary folder).
"""

import json
import os
import time

TTL_SECONDS = 24 * 60 * 60   # entries older than this are fetched again
CACHE_FILE = "lookups.json"


def cache_dir():
    return os.environ.get("IPINFO_CACHE_DIR", ".cache")


def _path():
    return os.path.join(cache_dir(), CACHE_FILE)


def _load():
    """Return the whole cache as a dict ({} if missing or damaged)."""
    try:
        with open(_path(), encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _save(store):
    os.makedirs(cache_dir(), exist_ok=True)
    tmp = _path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=2, ensure_ascii=False)
    os.replace(tmp, _path())  # write-then-rename so a crash never leaves half a file


def get(ip):
    """Return cached details for `ip`, or None if not cached or expired."""
    entry = _load().get(ip)
    if not isinstance(entry, dict) or not isinstance(entry.get("data"), dict):
        return None
    if time.time() - entry.get("saved_at", 0) > TTL_SECONDS:
        return None
    return dict(entry["data"])


def put(ip, details):
    """Save details for `ip`. Caching is optional, so disk errors are ignored."""
    store = _load()
    store[ip] = {"saved_at": time.time(), "data": details}
    try:
        _save(store)
    except OSError:
        pass


def clear():
    """Delete the cache file (used by tests; handy for troubleshooting)."""
    try:
        os.remove(_path())
    except FileNotFoundError:
        pass
