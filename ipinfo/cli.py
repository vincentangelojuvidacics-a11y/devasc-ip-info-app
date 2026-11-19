"""
cli.py - Entry point. Two ways to use the app:

1. Interactive menu (no arguments):
       python main.py

2. One-shot commands (good for scripts / automation):
       python main.py --me                 # my public IPv4 + IPv6 with details
       python main.py --lookup 8.8.8.8     # details for any IP
       python main.py --analyze 2001:db8::1  # offline analysis only
       python main.py --subnet 192.168.1.0/26
       python main.py --me --export json   # also save a report
       python main.py --lookup 8.8.8.8 --no-cache   # skip the 24-hour cache
       python main.py --bulk samples/ips.txt --export csv   # a whole list of IPs
"""

import argparse
import csv

from . import analyzer, api, exporter, formatter as fmt

# Results collected during this session so they can be exported at once.
session_results = []


# ----------------------------------------------------------------------
# Features (each menu item maps to one function)
# ----------------------------------------------------------------------
def show_my_ips(use_cache=True):
    """Feature 1: detect public IPv4 + IPv6, then show details for each."""
    fmt.info("Detecting your public IP addresses...")
    ipv4 = api.get_public_ip(4)
    ipv6 = api.get_public_ip(6)
    fmt.show_public_ips(ipv4, ipv6)

    if not ipv4 and not ipv6:
        fmt.error("No internet connection detected. Check your network and try again.")
        return

    for ip in (ipv4, ipv6):
        if ip:
            lookup_ip(ip, title=f"Details for your IPv{analyzer.validate_ip(ip).version}",
                      use_cache=use_cache)


def lookup_ip(ip_text, title=None, use_cache=True):
    """Feature 2: validate, analyze offline, then fetch online details."""
    ip = analyzer.validate_ip(ip_text)
    if ip is None:
        fmt.error(f"'{ip_text}' is not a valid IPv4 or IPv6 address.")
        return

    facts = analyzer.analyze(str(ip))
    hostname = analyzer.reverse_dns(str(ip)) or "No PTR record"
    # Private/loopback addresses have no public geolocation - skip the API call.
    if not ip.is_global:
        facts["Hostname (PTR)"] = hostname
        fmt.show_facts(facts, f"Analysis of {ip}")
        fmt.info(f"{facts['Type']} addresses are not on the public internet, "
                 "so there is no ISP/location data.")
        session_results.append({"ip": str(ip), **facts})
        return

    try:
        details = api.get_ip_details(str(ip), use_cache=use_cache)
    except api.IPLookupError as exc:
        fmt.error(f"Could not get online details: {exc}")
        facts["Hostname (PTR)"] = hostname
        fmt.show_facts(facts, f"Offline analysis of {ip}")
        return

    details["hostname"] = hostname
    fmt.show_details(details, title or f"Details for {ip}")
    fmt.show_facts(facts, "Technical analysis")
    session_results.append({**details, "type": facts["Type"]})


def analyze_only(ip_text):
    """Feature 3: offline analysis - works without internet."""
    try:
        fmt.show_facts(analyzer.analyze(ip_text), f"Analysis of {ip_text.strip()}")
    except ValueError as exc:
        fmt.error(str(exc))


def subnet_calc(cidr_text):
    """Feature 4: subnet calculator."""
    try:
        fmt.show_facts(analyzer.subnet_info(cidr_text), f"Subnet {cidr_text.strip()}")
    except ValueError as exc:
        fmt.error(f"Invalid network: {exc}")


CSV_HEADERS = {"ip", "ip address", "ip_address", "address"}


def read_ip_file(path):
    """
    Read IP addresses from a .txt file (one per line) or a .csv file (first column).
    Blank lines, '#' comments and duplicates are skipped.
    Returns (valid_ips, rejected_entries). Raises OSError if the file cannot be read.
    """
    with open(path, encoding="utf-8-sig", newline="") as f:
        if path.lower().endswith(".csv"):
            entries = [row[0] if row else "" for row in csv.reader(f)]
            if entries and entries[0].strip().lower() in CSV_HEADERS:
                entries = entries[1:]  # skip a header row such as "ip"
        else:
            entries = f.read().splitlines()

    valid, rejected, seen = [], [], set()
    for raw in entries:
        text = raw.split("#", 1)[0].strip()
        if not text:
            continue
        ip = analyzer.validate_ip(text)
        if ip is None:
            rejected.append(text)
        elif str(ip) not in seen:
            seen.add(str(ip))
            valid.append(str(ip))
    return valid, rejected


def _bulk_row(ip_text, use_cache):
    """Look up one address for bulk mode. Never raises: errors become a status."""
    ip = analyzer.validate_ip(ip_text)
    row = {"ip": ip_text, "type": analyzer.classify(ip),
           "hostname": analyzer.reverse_dns(ip_text) or "No PTR record"}
    if not ip.is_global:
        return {**row, "status": "offline (not public)"}
    try:
        details = api.get_ip_details(ip_text, use_cache=use_cache)
    except api.IPLookupError:
        return {**row, "status": "error"}
    status = "cached" if details.get("source", "").endswith("(cached)") else "ok"
    return {**details, **row, "status": status}


def bulk_lookup(path, use_cache=True):
    """Feature 6 (Activity 4): look up every IP address listed in a .txt/.csv file."""
    try:
        ips, rejected = read_ip_file(path)
    except OSError as exc:
        fmt.error(f"Cannot read '{path}': {exc.strerror or exc}")
        return []
    if rejected:
        shown = ", ".join(rejected[:5]) + (" ..." if len(rejected) > 5 else "")
        fmt.info(f"Skipped {len(rejected)} invalid entr{'y' if len(rejected) == 1 else 'ies'}: {shown}")
    if not ips:
        fmt.error("No valid IP addresses found in the file.")
        return []

    fmt.info(f"Looking up {len(ips)} address(es)...")
    rows = [_bulk_row(ip, use_cache) for ip in ips]
    session_results.extend(rows)
    fmt.show_bulk_summary(rows)
    return rows


def export_results(fmt_name):
    """Feature 5: save this session's lookups to reports/."""
    if not session_results:
        fmt.info("Nothing to export yet - do a lookup first.")
        return
    path = exporter.export_csv(session_results) if fmt_name == "csv" \
        else exporter.export_json(session_results)
    fmt.success(f"Saved {len(session_results)} result(s) to {path}")


# ----------------------------------------------------------------------
# Interactive menu
# ----------------------------------------------------------------------
MENU = """
[bold]Main Menu[/bold]
  [cyan]1[/cyan]  Show my public IPv4 / IPv6 address
  [cyan]2[/cyan]  Look up any IP address
  [cyan]3[/cyan]  Analyze an IP address (offline)
  [cyan]4[/cyan]  Subnet calculator
  [cyan]5[/cyan]  Export session results (JSON / CSV)
  [cyan]6[/cyan]  Bulk lookup from a .txt / .csv file
  [cyan]0[/cyan]  Exit
"""


def interactive():
    fmt.banner()
    while True:
        fmt.console.print(MENU)
        choice = fmt.console.input("[bold]Select an option: [/bold]").strip()
        if choice == "1":
            show_my_ips()
        elif choice == "2":
            lookup_ip(fmt.console.input("Enter IP address: "))
        elif choice == "3":
            analyze_only(fmt.console.input("Enter IP address: "))
        elif choice == "4":
            subnet_calc(fmt.console.input("Enter network in CIDR (e.g. 192.168.1.0/24): "))
        elif choice == "5":
            kind = fmt.console.input("Format [json/csv] (default json): ").strip().lower()
            export_results("csv" if kind == "csv" else "json")
        elif choice == "6":
            bulk_lookup(fmt.console.input("Path to .txt or .csv file: ").strip().strip('"'))
        elif choice in ("0", "q", "quit", "exit"):
            fmt.success("Goodbye!")
            break
        else:
            fmt.error("Invalid choice. Enter a number from the menu.")


# ----------------------------------------------------------------------
# Command-line arguments
# ----------------------------------------------------------------------
def build_parser():
    p = argparse.ArgumentParser(description="IPv4/IPv6 address information tool")
    p.add_argument("--me", action="store_true", help="show my public IPv4/IPv6 and details")
    p.add_argument("--lookup", metavar="IP", help="get details for any IP address")
    p.add_argument("--analyze", metavar="IP", help="offline analysis of an IP address")
    p.add_argument("--subnet", metavar="CIDR", help="subnet calculator, e.g. 10.0.0.0/22")
    p.add_argument("--bulk", metavar="FILE", help="look up every IP in a .txt or .csv file")
    p.add_argument("--export", choices=["json", "csv"], help="save results to reports/")
    p.add_argument("--no-cache", action="store_true",
                   help="ignore the 24-hour lookup cache and fetch fresh data")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    if not any([args.me, args.lookup, args.analyze, args.subnet, args.bulk]):
        try:
            interactive()
        except (KeyboardInterrupt, EOFError):
            fmt.console.print()
            fmt.success("Goodbye!")
        return

    if args.me:
        show_my_ips(use_cache=not args.no_cache)
    if args.lookup:
        lookup_ip(args.lookup, use_cache=not args.no_cache)
    if args.analyze:
        analyze_only(args.analyze)
    if args.subnet:
        subnet_calc(args.subnet)
    if args.bulk:
        bulk_lookup(args.bulk, use_cache=not args.no_cache)
    if args.export:
        export_results(args.export)
