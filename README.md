# IPv4 / IPv6 Address Information Tool

**DEVASC Project Activity 3 — Option 2: New Code**

This is a prototype command-line tool for network technicians. It shows the computer's current public IPv4 and IPv6 addresses, along with ISP, ASN, geolocation, and country details. It can also analyze any IP address offline and calculate subnets.

---

## Features

| # | Feature | Uses internet? |
|---|---------|----------------|
| 1 | Detect your public **IPv4 and IPv6** address | Yes (ipify) |
| 2 | Look up **any IP**: ISP, ASN, city, region, country and country code, coordinates with a Google Maps link, timezone, currency | Yes (ipapi.co, with ipwho.is as fallback) |
| 3 | **Offline analysis**: public, private, CGNAT, loopback, or link-local type; binary form; classful class; reverse DNS name; IPv6 expanded and compressed forms | No |
| 4 | **Subnet calculator**: mask, wildcard, broadcast, usable host range and count | No |
| 5 | **Export** session results to JSON or CSV in `reports/` | No |
| — | Colored tables (`rich`), input validation, automatic API fallback, friendly errors | — |

## Quick start

```bash
git clone <your-repo-url>
cd ip_address_app
pip install -r requirements.txt
python main.py              # interactive menu
```

One-shot commands:

```bash
python main.py --me                     # my public IPs + details
python main.py --lookup 8.8.8.8
python main.py --analyze 2001:db8::1
python main.py --subnet 192.168.10.0/26
python main.py --me --export csv        # also save a report
python main.py --help
```

Run the tests (they mock the APIs, so they work offline):

```bash
python -m pytest -v
```

> **IPv6 shows "Not available"?** That's normal. Many Philippine home and school networks don't provide IPv6 yet. Try it on mobile data to see an IPv6 result.

## APIs used (free, no API key)

| API | Purpose | Limit |
|-----|---------|-------|
| `api.ipify.org` / `api6.ipify.org` | Returns the caller's public IPv4 / IPv6 | Unlimited |
| `ipapi.co/<ip>/json/` | Geolocation, ISP (org), ASN, country, timezone | ~1,000 requests/day |
| `ipwho.is/<ip>` | Backup provider if ipapi.co fails or is rate-limited | ~10,000 requests/month |

## Project structure

```
ip_address_app/
├── main.py               # entry point
├── requirements.txt
├── ipinfo/
│   ├── api.py            # REST calls + converts each API's JSON to one standard format
│   ├── analyzer.py       # offline IP analysis + subnet calculator (ipaddress module)
│   ├── formatter.py      # all terminal output (colors, tables)
│   ├── exporter.py       # JSON / CSV reports
│   └── cli.py            # menu + command-line arguments, connects the modules
└── tests/test_app.py     # 24 unit tests (pytest)
```

**Design rule:** `api.py` and `analyzer.py` only return dicts and never print anything. All output goes through `formatter.py`. Because of this, each module can be developed on its own branch, and a future GUI or web version only has to replace `formatter.py` and `cli.py`.

## How data flows

```
user input → analyzer.validate_ip() → (if public) api.get_ip_details()
           → tries ipapi.co → falls back to ipwho.is → normalized dict
           → formatter.show_details()  +  analyzer.analyze()
           → saved in session_results → exporter (optional)
```

Private, loopback, and other non-public addresses skip the API call, because they have no public location data. This also saves API quota.

## How to continue this project (for future teams)

- **Add an API provider:** in `api.py`, write `_fetch_x()` and `_normalize_x()` and add them to the `PROVIDERS` list.
- **Add a menu option:** write a function in `cli.py`, add it to `MENU` and `interactive()`, and optionally add a matching `--flag` in `build_parser()`.
- **Change how output looks:** edit `formatter.py` only.
- Add a test in `tests/test_app.py` for every new feature, and mock any network calls.

## Backlog (future enhancements, for Project Activity 4)

1. **IP reputation / threat check** using the AbuseIPDB or VirusTotal API (requires an API key stored in a `.env` file)
2. **VPN / proxy / Tor detection** (e.g. proxycheck.io)
3. **Bulk lookup** from a `.txt` or `.csv` file of IPs
4. **Reverse DNS and WHOIS** lookups (`socket.gethostbyaddr`, RDAP)
5. **Ping / traceroute** to a looked-up IP, with latency
6. **Local network info**: private IP, default gateway, DNS servers
7. **GUI or web dashboard** (Tkinter or Flask) with a map view
8. **Caching** of lookups to save API quota
9. **Lookup history** stored in SQLite
10. **Packaging** as a `pip`-installable CLI and/or Docker image, with GitHub Actions CI running the tests

## Team

| Member | Role | Branch | Files |
|--------|------|--------|-------|
| Juvida | Scrum Leader / Integrator | `feature/cli` (+ merges into `main`) | `main.py`, `ipinfo/cli.py`, `requirements.txt` |
| Almonte | Developer (API) | `feature/api` | `ipinfo/api.py`, `ipinfo/exporter.py` |
| Navarro | Developer (Analysis & UI) | `feature/analyzer` | `ipinfo/analyzer.py`, `ipinfo/formatter.py` |
| Reyes | QA & Documentation | `feature/tests-docs` | `tests/test_app.py`, `README.md` |
