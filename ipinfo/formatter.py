"""
formatter.py - Everything the user SEES is built here (colors, tables, panels).

Uses the `rich` library. If a future team wants a GUI or web version,
only this module needs to be replaced - api.py and analyzer.py return
plain dicts and do not print anything.
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

# Friendly labels for api.py's STANDARD_FIELDS, in display order.
DETAIL_LABELS = [
    ("ip", "IP Address"),
    ("version", "Version"),
    ("isp", "ISP / Organization"),
    ("asn", "ASN"),
    ("city", "City"),
    ("region", "Region"),
    ("country", "Country"),
    ("country_code", "Country Code"),
    ("postal", "Postal Code"),
    ("coords", "Coordinates"),
    ("timezone", "Timezone"),
    ("utc_offset", "UTC Offset"),
    ("currency", "Currency"),
]


def _value(v):
    """Show missing values as a dim dash instead of 'None'."""
    return "[dim]-[/dim]" if v in (None, "") else str(v)


def banner():
    console.print(Panel.fit(
        "[bold cyan]IPv4 / IPv6 Address Information Tool[/bold cyan]\n"
        "[dim]DEVASC Project Activity 3 - Network Technician Prototype[/dim]",
        border_style="cyan",
    ))


def show_public_ips(ipv4, ipv6):
    table = Table(title="Your Public IP Addresses", header_style="bold magenta")
    table.add_column("Protocol", style="bold")
    table.add_column("Address")
    table.add_column("Status")
    table.add_row("IPv4", _value(ipv4),
                  "[green]Available[/green]" if ipv4 else "[red]Not detected[/red]")
    table.add_row("IPv6", _value(ipv6),
                  "[green]Available[/green]" if ipv6 else "[yellow]Not available on this network[/yellow]")
    console.print(table)


def show_details(details, title="IP Details"):
    """Print the normalized dict from api.get_ip_details() as a two-column table."""
    row_data = dict(details)
    lat, lon = details.get("latitude"), details.get("longitude")
    row_data["coords"] = f"{lat}, {lon}" if lat is not None and lon is not None else None

    table = Table(title=title, show_header=False, header_style="bold magenta")
    table.add_column("Field", style="bold cyan", no_wrap=True)
    table.add_column("Value")
    for key, label in DETAIL_LABELS:
        table.add_row(label, _value(row_data.get(key)))
    console.print(table)

    if lat is not None and lon is not None:
        console.print(f"[dim]Map: https://www.google.com/maps?q={lat},{lon}[/dim]")
    console.print(f"[dim]Data source: {details.get('source', '?')}[/dim]\n")


def show_facts(facts, title):
    """Generic key/value table used for analyzer output and subnet info."""
    table = Table(title=title, show_header=False)
    table.add_column("Field", style="bold green", no_wrap=True)
    table.add_column("Value", overflow="fold")
    for key, val in facts.items():
        table.add_row(key, _value(val))
    console.print(table)


def info(msg):
    console.print(f"[cyan]i[/cyan] {msg}")


def success(msg):
    console.print(f"[green]OK[/green] {msg}")


def error(msg):
    console.print(f"[bold red]ERROR[/bold red] {msg}")
