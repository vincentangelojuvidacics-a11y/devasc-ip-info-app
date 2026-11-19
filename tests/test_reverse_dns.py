"""
Tests for reverse DNS (analyzer.reverse_dns).

socket.gethostbyaddr is mocked, so no real DNS query is made and the
results are the same on every machine, including GitHub's runners.
"""

import socket
import time
from unittest.mock import patch

import pytest

from ipinfo import analyzer


@patch("ipinfo.analyzer.socket.gethostbyaddr",
       return_value=("dns.google", [], ["8.8.8.8"]))
def test_reverse_dns_found(mock_lookup):
    assert analyzer.reverse_dns("8.8.8.8") == "dns.google"
    mock_lookup.assert_called_once_with("8.8.8.8")


@patch("ipinfo.analyzer.socket.gethostbyaddr",
       side_effect=socket.herror(1, "Unknown host"))
def test_reverse_dns_no_ptr(_):
    assert analyzer.reverse_dns("203.0.113.9") is None


def test_reverse_dns_timeout():
    def slow_lookup(_ip):
        time.sleep(1)
        return ("too-late.example", [], [])

    with patch("ipinfo.analyzer.socket.gethostbyaddr", side_effect=slow_lookup):
        started = time.monotonic()
        assert analyzer.reverse_dns("8.8.4.4", timeout=0.1) is None
        assert time.monotonic() - started < 0.9   # we did not wait for the slow server


def test_reverse_dns_invalid_ip():
    with pytest.raises(ValueError):
        analyzer.reverse_dns("999.1.1.1")
