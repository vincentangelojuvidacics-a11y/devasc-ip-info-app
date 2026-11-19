"""
Shared pytest setup (applies to every test).

Each test gets its own empty lookup cache in a temporary folder, so tests
never read results saved by a previous test (or by a real run of the app)
and never write a .cache/ folder into the project.
"""

import pytest


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("IPINFO_CACHE_DIR", str(tmp_path / "cache"))
    yield tmp_path / "cache"
