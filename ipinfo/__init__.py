"""
ipinfo - IPv4/IPv6 Address Information Tool (DEVASC Project Activities 3 and 4)

Package layout (one module per team member / feature branch):
    api.py        -> REST API calls (ipify for public IPs, ipapi.co / ipwho.is for details)
    cache.py      -> 24-hour JSON cache of successful lookups (Activity 4)
    analyzer.py   -> Offline IP analysis using Python's built-in `ipaddress` module,
                     plus reverse_dns() for hostnames (Activity 4)
    formatter.py  -> Colored, table-based terminal output (rich library)
    exporter.py   -> Save results to JSON / CSV
    cli.py        -> Interactive menu + command-line arguments + bulk lookup (entry point)
"""

__version__ = "1.1.0"
