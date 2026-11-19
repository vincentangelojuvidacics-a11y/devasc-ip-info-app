"""
Tests for bulk lookup (cli.read_ip_file / cli.bulk_lookup) and the new options.

api.get_ip_details and analyzer.reverse_dns are mocked: no network is used.
"""

from unittest.mock import patch

import pytest

from ipinfo import api, cli


@pytest.fixture(autouse=True)
def no_dns_and_empty_session(monkeypatch):
    monkeypatch.setattr(cli.analyzer, "reverse_dns", lambda ip, timeout=3: None)
    monkeypatch.setattr(cli, "session_results", [])


def test_read_ip_file_txt(tmp_path):
    f = tmp_path / "ips.txt"
    f.write_text("# my list\n8.8.8.8\n\n1.1.1.1   # cloudflare\n", encoding="utf-8")
    assert cli.read_ip_file(str(f)) == (["8.8.8.8", "1.1.1.1"], [])


def test_read_ip_file_csv(tmp_path):
    f = tmp_path / "ips.csv"
    f.write_text("ip,note\n8.8.8.8,google\n2001:db8::1,docs\n", encoding="utf-8")
    assert cli.read_ip_file(str(f)) == (["8.8.8.8", "2001:db8::1"], [])


def test_read_ip_file_rejects_invalid_and_duplicates(tmp_path):
    f = tmp_path / "ips.txt"
    f.write_text("8.8.8.8\n192.168.1.300\nhello\n8.8.8.8\n", encoding="utf-8")
    valid, rejected = cli.read_ip_file(str(f))
    assert valid == ["8.8.8.8"]
    assert rejected == ["192.168.1.300", "hello"]


@patch("ipinfo.cli.api.get_ip_details")
def test_bulk_private_ip_skips_api(mock_details, tmp_path):
    f = tmp_path / "ips.txt"
    f.write_text("192.168.1.10\n10.0.0.1\n", encoding="utf-8")
    rows = cli.bulk_lookup(str(f))
    mock_details.assert_not_called()
    assert [r["status"] for r in rows] == ["offline (not public)"] * 2


@patch("ipinfo.cli.api.get_ip_details")
def test_bulk_continues_after_error(mock_details, tmp_path):
    mock_details.side_effect = [
        api.IPLookupError("All providers failed"),
        {"ip": "1.1.1.1", "country": "Australia", "isp": "Cloudflare", "source": "ipapi.co"},
    ]
    f = tmp_path / "ips.txt"
    f.write_text("8.8.8.8\n1.1.1.1\n", encoding="utf-8")
    rows = cli.bulk_lookup(str(f))
    assert [r["status"] for r in rows] == ["error", "ok"]
    assert rows[1]["isp"] == "Cloudflare"
    assert len(cli.session_results) == 2      # both rows can be exported


def test_bulk_missing_file(tmp_path):
    assert cli.bulk_lookup(str(tmp_path / "does_not_exist.txt")) == []


def test_cli_parses_bulk_and_no_cache():
    args = cli.build_parser().parse_args(["--bulk", "ips.txt", "--no-cache", "--export", "csv"])
    assert args.bulk == "ips.txt" and args.no_cache is True and args.export == "csv"
