"""
Tests for the 24-hour lookup cache (cache.py + api.get_ip_details).

The API is mocked and conftest.py gives every test an empty cache folder,
so these tests run offline and in any order.
"""

import time
from unittest.mock import MagicMock, patch

import requests

from ipinfo import api, cache

IPAPI_PAYLOAD = {
    "ip": "8.8.8.8", "version": "IPv4", "city": "Mountain View",
    "country_name": "United States", "org": "GOOGLE", "asn": "AS15169",
}


def _ok(payload=IPAPI_PAYLOAD):
    resp = MagicMock()
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    return resp


@patch("ipinfo.api.requests.get")
def test_cache_miss_then_hit(mock_get):
    mock_get.return_value = _ok()
    first = api.get_ip_details("8.8.8.8")
    second = api.get_ip_details("8.8.8.8")
    assert mock_get.call_count == 1                 # second lookup used no API call
    assert first["source"] == "ipapi.co"
    assert second["source"] == "ipapi.co (cached)"
    assert second["isp"] == "GOOGLE"


@patch("ipinfo.api.requests.get")
def test_cache_expired_refetches(mock_get, monkeypatch):
    mock_get.return_value = _ok()
    api.get_ip_details("8.8.8.8")
    later = time.time() + cache.TTL_SECONDS + 60    # pretend 24 hours + 1 minute passed
    monkeypatch.setattr(cache.time, "time", lambda: later)
    assert api.get_ip_details("8.8.8.8")["source"] == "ipapi.co"
    assert mock_get.call_count == 2


def test_cache_corrupt_file_ignored(isolated_cache):
    isolated_cache.mkdir(parents=True)
    (isolated_cache / cache.CACHE_FILE).write_text("{ this is not json", encoding="utf-8")
    assert cache.get("8.8.8.8") is None             # damaged file = empty cache
    cache.put("8.8.8.8", {"ip": "8.8.8.8", "source": "ipapi.co"})
    assert cache.get("8.8.8.8")["ip"] == "8.8.8.8"  # and it is rebuilt


@patch("ipinfo.api.requests.get")
def test_no_cache_bypasses_cache(mock_get):
    mock_get.return_value = _ok()
    api.get_ip_details("8.8.8.8")
    fresh = api.get_ip_details("8.8.8.8", use_cache=False)
    assert mock_get.call_count == 2
    assert fresh["source"] == "ipapi.co"


@patch("ipinfo.api.requests.get", side_effect=requests.Timeout)
def test_failed_lookup_not_cached(_):
    try:
        api.get_ip_details("8.8.8.8")
    except api.IPLookupError:
        pass
    assert cache.get("8.8.8.8") is None
