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
"""

import argparse

from . import analyzer, api, exporter, formatter as fmt

# Results collected during this session so they can be exported at once.
session_results = []


# ----------------------------------------------------------------------
# Features (each menu item maps to one function)
# ----------------------------------------------------------------------
def show_my_ips():
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
            lookup_ip(ip, title=f"Details for your IPv{analyzer.validate_ip(ip).version}")


def lookup_ip(ip_text, title=None):
    """Feature 2: validate, analyze offline, then fetch online details."""
    ip = analyzer.validate_ip(ip_text)
    if ip is None:
        fmt.error(f"'{ip_text}' is not a valid IPv4 or IPv6 address.")
        return

    facts = analyzer.analyze(str(ip))
    # Private/loopback addresses have no public geolocation - skip the API call.
    if not ip.is_global:
        fmt.show_facts(facts, f"Analysis of {ip}")
        fmt.info(f"{facts['Type']} addresses are not on the public internet, "
                 "so there is no ISP/location data.")
        session_results.append({"ip": str(ip), **facts})
        return

    try:
        details = api.get_ip_details(str(ip))
    except api.IPLookupError as exc:
        fmt.error(f"Could not get online details: {exc}")
        fmt.show_facts(facts, f"Offline analysis of {ip}")
        return

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
    p.add_argument("--export", choices=["json", "csv"], help="save results to reports/")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    if not any([args.me, args.lookup, args.analyze, args.subnet]):
        try:
            interactive()
        except (KeyboardInterrupt, EOFError):
            fmt.console.print()
            fmt.success("Goodbye!")
        return

    if args.me:
        show_my_ips()
    if args.lookup:
        lookup_ip(args.lookup)
    if args.analyze:
        analyze_only(args.analyze)
    if args.subnet:
        subnet_calc(args.subnet)
    if args.export:
        export_results(args.export)
