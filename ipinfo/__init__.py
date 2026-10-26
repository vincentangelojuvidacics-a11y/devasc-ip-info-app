"""
ipinfo - IPv4/IPv6 Address Information Tool (DEVASC Project Activity 3, Option 2)

Package layout (one module per team member / feature branch):
    api.py        -> REST API calls (ipify for public IPs, ipapi.co / ipwho.is for details)
    analyzer.py   -> Offline IP analysis using Python's built-in `ipaddress` module
    formatter.py  -> Colored, table-based terminal output (rich library)
    exporter.py   -> Save results to JSON / CSV
    cli.py        -> Interactive menu + command-line arguments (entry point)
"""

__version__ = "1.0.0"
