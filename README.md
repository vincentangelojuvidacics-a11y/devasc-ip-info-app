# IPv4 / IPv6 Address Information Tool

![CI](https://github.com/vincentangelojuvidacics-a11y/devasc-ip-info-app/actions/workflows/ci.yml/badge.svg)

**DEVASC Project Activity 3 — Option 2: New Code · extended in Project Activity 4 (automated testing and CI/CD)**

This is a prototype command-line tool for network technicians. It shows the computer's current public IPv4 and IPv6 addresses, along with ISP, ASN, geolocation, and country details. It can also analyze any IP address offline, calculate subnets, look up a whole file of addresses at once, and show each address's hostname.

---

## Features

| # | Feature | Uses internet? |
|---|---------|----------------|
| 1 | Detect your public **IPv4 and IPv6** address | Yes (ipify) |
| 2 | Look up **any IP**: ISP, ASN, city, region, country and country code, coordinates with a Google Maps link, timezone, currency | Yes (ipapi.co, with ipwho.is as fallback) |
| 3 | **Offline analysis**: public, private, CGNAT, loopback, or link-local type; binary form; classful class; reverse DNS name; IPv6 expanded and compressed forms | No |
| 4 | **Subnet calculator**: mask, wildcard, broadcast, usable host range and count | No |
| 5 | **Export** session results to JSON or CSV in `reports/` | No |
| 6 | **Bulk lookup** *(Activity 4)*: every IP in a `.txt` or `.csv` file, with one summary table | Yes, for public IPs |
| 7 | **Lookup cache** *(Activity 4)*: successful lookups are reused for 24 hours (`.cache/lookups.json`) to save API quota | No (that is the point) |
| 8 | **Reverse DNS** *(Activity 4)*: hostname (PTR record) of an IP, e.g. 8.8.8.8 → dns.google, with a 3-second limit | Yes (DNS) |
| — | Colored tables (`rich`), input validation, automatic API fallback, friendly errors | — |

## Quick start

```bash
git clone https://github.com/vincentangelojuvidacics-a11y/devasc-ip-info-app.git
cd devasc-ip-info-app
pip install -r requirements.txt
python main.py              # interactive menu
```

One-shot commands:

```bash
python main.py --me                     # my public IPs + details
python main.py --lookup 8.8.8.8         # includes Hostname (PTR); 2nd run says "(cached)"
python main.py --lookup 8.8.8.8 --no-cache   # ignore the cache, fetch fresh data
python main.py --analyze 2001:db8::1
python main.py --subnet 192.168.10.0/26
python main.py --bulk samples/ips.txt --export csv   # a whole list, saved as a report
python main.py --me --export csv        # also save a report
python main.py --help
```

**Bulk file format:** one address per line in a `.txt` file, or the first column of a `.csv` file (a header such as `ip` is skipped). Blank lines, `#` comments and duplicates are ignored; invalid entries are listed and skipped. Private addresses are analyzed offline without an API call. See `samples/ips.txt`.

Run the tests (they mock the APIs and DNS, so they work offline):

```bash
python -m pytest -v
```

> **IPv6 shows "Not available"?** That's normal. Many Philippine home and school networks don't provide IPv6 yet. Try it on mobile data to see an IPv6 result.

## CI/CD pipeline (GitHub Actions)

`.github/workflows/ci.yml` runs automatically on **every push to any branch** and **every pull request into `main`**:

| Job | What it does | Runs when |
|-----|--------------|-----------|
| `lint` | `flake8` checks for syntax errors and undefined names | always |
| `test` | `python -m pytest -v` on Python 3.10, 3.11 and 3.12; uploads the test report | after `lint` passes |
| `package` | uploads the tested app as the `ipinfo-app` build artifact | after a merge to `main`, if every test passed |

**Branch protection on `main`** (Settings → Branches): require a pull request with 1 approval, require the `lint` and `test (3.10)`, `test (3.11)`, `test (3.12)` status checks to pass, require branches to be up to date, and do not allow bypassing the rule. If any test fails, the pull request cannot be merged.

> GitHub only lists a status check in branch protection after the workflow has run once, so push the workflow first, then add the required checks.

## APIs used (free, no API key)

| API | Purpose | Limit |
|-----|---------|-------|
| `api.ipify.org` / `api6.ipify.org` | Returns the caller's public IPv4 / IPv6 | Unlimited |
| `ipapi.co/<ip>/json/` | Geolocation, ISP (org), ASN, country, timezone | ~1,000 requests/day |
| `ipwho.is/<ip>` | Backup provider if ipapi.co fails or is rate-limited | ~10,000 requests/month |

Reverse DNS uses Python's built-in `socket.gethostbyaddr()`; no API is involved.

## Project structure

```
devasc-ip-info-app/
├── main.py               # entry point
├── requirements.txt
├── conftest.py           # gives every test its own empty cache folder
├── .github/workflows/
│   └── ci.yml            # CI/CD pipeline (lint, test matrix, package)
├── ipinfo/
│   ├── api.py            # REST calls + converts each API's JSON to one standard format
│   ├── cache.py          # 24-hour JSON cache of successful lookups
│   ├── analyzer.py       # offline IP analysis, subnet calculator, reverse_dns()
│   ├── formatter.py      # all terminal output (colors, tables, bulk summary)
│   ├── exporter.py       # JSON / CSV reports
│   └── cli.py            # menu + command-line arguments, bulk lookup
├── samples/ips.txt       # sample list for the bulk lookup demo
└── tests/
    ├── test_app.py       # 24 tests from Activity 3
    ├── test_cache.py     # 5 cache tests
    ├── test_reverse_dns.py  # 4 reverse DNS tests
    └── test_bulk.py      # 7 bulk lookup / option tests  (40 tests in total)
```

**Design rule:** `api.py` and `analyzer.py` only return dicts and never print anything. All output goes through `formatter.py`. Because of this, each module can be developed on its own branch, and a future GUI or web version only has to replace `formatter.py` and `cli.py`.

## How data flows

```
user input → analyzer.validate_ip() → analyzer.reverse_dns() (hostname)
           → (if public) api.get_ip_details()
               → cache hit (< 24 h old)? return it, source "... (cached)"
               → else tries ipapi.co → falls back to ipwho.is → normalized dict → saved in cache
           → formatter.show_details()  +  analyzer.analyze()
           → saved in session_results → exporter (optional)
```

Private, loopback, and other non-public addresses skip the API call, because they have no public location data. This also saves API quota. Failed lookups are never cached.

## How to continue this project (for future teams)

- **Add an API provider:** in `api.py`, write `_fetch_x()` and `_normalize_x()` and add them to the `PROVIDERS` list.
- **Add a menu option:** write a function in `cli.py`, add it to `MENU` and `interactive()`, and optionally add a matching `--flag` in `build_parser()`.
- **Change how output looks:** edit `formatter.py` only.
- **Clear the cache:** delete the `.cache/` folder, or set `IPINFO_CACHE_DIR` to use another folder.
- **Testing rule ("no test, no merge"):** add tests for every new feature in `tests/`, and mock every network call (`requests.get`, `socket.gethostbyaddr`) so the tests pass offline and on GitHub's runners. The pipeline blocks the merge if any test fails.

## Backlog

Done in Project Activity 4:

- ~~3. **Bulk lookup** from a `.txt` or `.csv` file of IPs~~
- ~~4. **Reverse DNS**~~ lookups (`socket.gethostbyaddr`). WHOIS/RDAP is still open.
- ~~8. **Caching** of lookups to save API quota~~
- ~~10. **GitHub Actions CI** running the tests~~ (packaging as a pip-installable CLI / Docker image is still open)

Still open:

1. **IP reputation / threat check** using the AbuseIPDB or VirusTotal API (requires an API key stored in a `.env` file, and as a GitHub Actions secret)
2. **VPN / proxy / Tor detection** (e.g. proxycheck.io)
4. **WHOIS** lookups (RDAP)
5. **Ping / traceroute** to a looked-up IP, with latency
6. **Local network info**: private IP, default gateway, DNS servers
7. **GUI or web dashboard** (Tkinter or Flask) with a map view
9. **Lookup history** stored in SQLite
10. **Packaging** as a `pip`-installable CLI and/or Docker image

## Team

| Member | Role | Branch | Files |
|--------|------|--------|-------|
| Juvida | Scrum Leader / Integrator | `feature/cli` (+ merges into `main`) | `main.py`, `ipinfo/cli.py`, `requirements.txt` |
| Almonte | Developer (API) | `feature/api` | `ipinfo/api.py`, `ipinfo/exporter.py` |
| Navarro | Developer (Analysis & UI) | `feature/analyzer` | `ipinfo/analyzer.py`, `ipinfo/formatter.py` |
| Reyes | QA & Documentation | `feature/tests-docs` | `tests/test_app.py`, `README.md` |

### Project Activity 4 branches

| Branch | Feature | Files |
|--------|---------|-------|
| `feature/ci-pipeline` | GitHub Actions CI/CD pipeline | `.github/workflows/ci.yml` |
| `feature/cache` | 24-hour lookup cache, `--no-cache` | `ipinfo/cache.py`, `ipinfo/api.py`, `conftest.py`, `tests/test_cache.py` |
| `feature/reverse-dns` | Reverse DNS (PTR) lookup | `ipinfo/analyzer.py`, `ipinfo/formatter.py`, `tests/test_reverse_dns.py` |
| `feature/bulk-lookup` | Bulk lookup, `--bulk`, menu option 6 | `ipinfo/cli.py`, `ipinfo/formatter.py`, `samples/ips.txt`, `tests/test_bulk.py` |
| `docs/activity-4` | This README | `README.md`, `ipinfo/__init__.py` |
