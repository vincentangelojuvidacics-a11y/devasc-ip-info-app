"""
api.py - All REST API communication lives here.

APIs used (all free, no API key needed):
    1. ipify       - returns ONLY the caller's public IP
         IPv4: https://api.ipify.org?format=json
         IPv6: https://api6.ipify.org?format=json  (fails if you have no IPv6 connectivity)
    2. ipapi.co    - returns details (city, ISP/org, ASN, country, timezone...) for an IP
         https://ipapi.co/<ip>/json/        (free tier: ~1,000 requests/day)
    3. ipwho.is    - backup details provider, used automatically if ipapi.co fails
         https://ipwho.is/<ip>              (or is rate-limited)

Every function returns plain Python dicts so the other modules never
have to know which API produced the data (see `_normalize_*` helpers).

HOW TO ADD A NEW PROVIDER (for future teams):
    1. Write a `_fetch_<provider>(ip)` function that returns the raw JSON.
    2. Write a `_normalize_<provider>(raw)` that maps it to STANDARD_FIELDS.
    3. Add it to the PROVIDERS list below. Providers are tried in order.
"""

import requests

TIMEOUT = 8  # seconds - keep the app responsive on slow connections
HEADERS = {"User-Agent": "DEVASC-IP-Info-App/1.0"}

IPV4_URL = "https://api.ipify.org?format=json"
IPV6_URL = "https://api6.ipify.org?format=json"

# Every provider is converted into these keys so formatter.py stays simple.
STANDARD_FIELDS = [
    "ip", "version", "city", "region", "country", "country_code",
    "postal", "latitude", "longitude", "timezone", "utc_offset",
    "isp", "asn", "currency", "source",
]


class IPLookupError(Exception):
    """Raised when every provider fails for a lookup."""


# ----------------------------------------------------------------------
# 1. Public IP discovery
# ----------------------------------------------------------------------
def get_public_ip(version=4):
    """
    Return this computer's public IP as a string, or None if unavailable.

    version=4 -> IPv4 address via api.ipify.org
    version=6 -> IPv6 address via api6.ipify.org
    None for IPv6 is NORMAL: many home ISPs in the PH still do not
    give customers IPv6, so the request simply cannot connect.
    """
    url = IPV4_URL if version == 4 else IPV6_URL
    try:
        response = requests.get(url, timeout=TIMEOUT, headers=HEADERS)
        response.raise_for_status()
        return response.json().get("ip")
    except (requests.RequestException, ValueError):
        return None


# ----------------------------------------------------------------------
# 2. Provider-specific fetch + normalize functions
# ----------------------------------------------------------------------
def _fetch_ipapi(ip):
    response = requests.get(f"https://ipapi.co/{ip}/json/", timeout=TIMEOUT, headers=HEADERS)
    response.raise_for_status()
    data = response.json()
    # ipapi.co signals errors (rate limit, reserved IP) inside a 200 response
    if data.get("error"):
        raise IPLookupError(data.get("reason", "ipapi.co error"))
    return data


def _normalize_ipapi(raw):
    return {
        "ip": raw.get("ip"),
        "version": raw.get("version"),
        "city": raw.get("city"),
        "region": raw.get("region"),
        "country": raw.get("country_name"),
        "country_code": raw.get("country_code"),
        "postal": raw.get("postal"),
        "latitude": raw.get("latitude"),
        "longitude": raw.get("longitude"),
        "timezone": raw.get("timezone"),
        "utc_offset": raw.get("utc_offset"),
        "isp": raw.get("org"),
        "asn": raw.get("asn"),
        "currency": raw.get("currency"),
        "source": "ipapi.co",
    }


def _fetch_ipwhois(ip):
    response = requests.get(f"https://ipwho.is/{ip}", timeout=TIMEOUT, headers=HEADERS)
    response.raise_for_status()
    data = response.json()
    if data.get("success") is False:
        raise IPLookupError(data.get("message", "ipwho.is error"))
    return data


def _normalize_ipwhois(raw):
    conn = raw.get("connection") or {}
    tz = raw.get("timezone") or {}
    asn = conn.get("asn")
    return {
        "ip": raw.get("ip"),
        "version": raw.get("type"),
        "city": raw.get("city"),
        "region": raw.get("region"),
        "country": raw.get("country"),
        "country_code": raw.get("country_code"),
        "postal": raw.get("postal"),
        "latitude": raw.get("latitude"),
        "longitude": raw.get("longitude"),
        "timezone": tz.get("id"),
        "utc_offset": tz.get("utc"),
        "isp": conn.get("isp") or conn.get("org"),
        "asn": f"AS{asn}" if asn else None,
        "currency": (raw.get("currency") or {}).get("code"),
        "source": "ipwho.is",
    }


# Order = priority. First provider that succeeds wins.
PROVIDERS = [
    ("ipapi.co", _fetch_ipapi, _normalize_ipapi),
    ("ipwho.is", _fetch_ipwhois, _normalize_ipwhois),
]


# ----------------------------------------------------------------------
# 3. Public function used by the rest of the app
# ----------------------------------------------------------------------
def get_ip_details(ip):
    """
    Look up geolocation / ISP / ASN details for `ip`.
    Tries each provider in PROVIDERS; raises IPLookupError if all fail.
    """
    errors = []
    for name, fetch, normalize in PROVIDERS:
        try:
            return normalize(fetch(ip))
        except (requests.RequestException, ValueError, IPLookupError) as exc:
            # Keep the message short: exception type + reason, not the full traceback text
            reason = str(exc).split("(Caused by")[0].strip()[:60] or type(exc).__name__
            errors.append(f"{name} ({type(exc).__name__}: {reason})")
    raise IPLookupError("All providers failed -> " + " | ".join(errors))
