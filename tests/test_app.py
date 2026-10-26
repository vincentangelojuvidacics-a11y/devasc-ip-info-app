"""
Unit tests (QA). Run with:  python -m pytest -v

API calls are MOCKED, so these tests run offline and never use up
the free-tier request quota.
"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from ipinfo import analyzer, api, exporter


# ---------------- analyzer.py ----------------
@pytest.mark.parametrize("text,ok", [
    ("8.8.8.8", True), ("2001:4860:4860::8888", True), (" 1.1.1.1 ", True),
    ("192.168.1.300", False), ("hello", False), ("", False),
])
def test_validate_ip(text, ok):
    assert (analyzer.validate_ip(text) is not None) == ok


@pytest.mark.parametrize("ip,expected", [
    ("8.8.8.8", "Public"), ("192.168.1.10", "Private"), ("127.0.0.1", "Loopback"),
    ("169.254.1.1", "Link-local"), ("100.64.5.5", "CGNAT"), ("::1", "Loopback"),
    ("fe80::1", "Link-local"), ("224.0.0.5", "Multicast"),
])
def test_classify(ip, expected):
    assert expected in analyzer.classify(analyzer.validate_ip(ip))


def test_analyze_ipv4_binary_and_class():
    facts = analyzer.analyze("192.168.1.1")
    assert facts["Binary"] == "11000000.10101000.00000001.00000001"
    assert facts["Classful class"] == "C"


def test_analyze_ipv6_expanded():
    facts = analyzer.analyze("2001:db8::1")
    assert facts["Expanded form"] == "2001:0db8:0000:0000:0000:0000:0000:0001"


def test_analyze_invalid_raises():
    with pytest.raises(ValueError):
        analyzer.analyze("999.1.1.1")


def test_subnet_info_26():
    info = analyzer.subnet_info("192.168.10.0/26")
    assert info["Subnet mask"] == "255.255.255.192"
    assert info["Broadcast"] == "192.168.10.63"
    assert info["Usable hosts"] == "62"


# ---------------- api.py (mocked) ----------------
def _mock_response(payload):
    resp = MagicMock()
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    return resp


@patch("ipinfo.api.requests.get")
def test_get_public_ip(mock_get):
    mock_get.return_value = _mock_response({"ip": "203.0.113.5"})
    assert api.get_public_ip(4) == "203.0.113.5"


@patch("ipinfo.api.requests.get", side_effect=requests.ConnectionError)
def test_get_public_ipv6_unavailable_returns_none(_):
    assert api.get_public_ip(6) is None


@patch("ipinfo.api.requests.get")
def test_details_from_ipapi(mock_get):
    mock_get.return_value = _mock_response({
        "ip": "8.8.8.8", "version": "IPv4", "city": "Mountain View",
        "country_name": "United States", "org": "GOOGLE", "asn": "AS15169",
    })
    d = api.get_ip_details("8.8.8.8")
    assert d["isp"] == "GOOGLE" and d["asn"] == "AS15169" and d["source"] == "ipapi.co"


@patch("ipinfo.api.requests.get")
def test_details_falls_back_to_ipwhois(mock_get):
    mock_get.side_effect = [
        _mock_response({"error": True, "reason": "RateLimited"}),           # ipapi.co
        _mock_response({"success": True, "ip": "1.1.1.1", "type": "IPv4",   # ipwho.is
                        "connection": {"asn": 13335, "isp": "Cloudflare"}}),
    ]
    d = api.get_ip_details("1.1.1.1")
    assert d["source"] == "ipwho.is" and d["asn"] == "AS13335"


@patch("ipinfo.api.requests.get", side_effect=requests.Timeout)
def test_details_all_fail(_):
    with pytest.raises(api.IPLookupError):
        api.get_ip_details("8.8.8.8")


# ---------------- exporter.py ----------------
def test_export_json_and_csv(tmp_path, monkeypatch):
    monkeypatch.setattr(exporter, "REPORT_DIR", str(tmp_path))
    recs = [{"ip": "8.8.8.8", "isp": "GOOGLE"}, {"ip": "10.0.0.1", "Type": "Private"}]
    assert exporter.export_json(recs).endswith(".json")
    csv_path = exporter.export_csv(recs)
    header = open(csv_path, encoding="utf-8").readline().strip()
    assert header == "ip,isp,Type"
