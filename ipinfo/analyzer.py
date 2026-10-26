"""
analyzer.py - Offline IP address analysis (no internet needed).

Uses Python's built-in `ipaddress` module to give network technicians
the "textbook" facts about an address: version, type (public/private/
loopback/...), binary form, reverse DNS pointer name, and for IPv4 the
legacy class and default subnet info.

This is also how the app VALIDATES user input before calling any API,
so we never waste an API request on a typo like "192.168.1.300".
"""

import ipaddress


def validate_ip(text):
    """Return an ip_address object if `text` is a valid IPv4/IPv6 address, else None."""
    try:
        return ipaddress.ip_address(text.strip())
    except (ValueError, AttributeError):
        return None


def classify(ip):
    """Return a human-readable address type, most specific first."""
    if ip.is_loopback:
        return "Loopback"
    if ip.is_link_local:
        return "Link-local"
    if ip.is_multicast:
        return "Multicast"
    if ip.is_unspecified:
        return "Unspecified"
    if ip.is_reserved:
        return "Reserved"
    if ip.version == 4 and ipaddress.ip_network("100.64.0.0/10").supernet_of(
        ipaddress.ip_network(f"{ip}/32")
    ):
        return "Shared / CGNAT (RFC 6598)"
    if ip.is_private:
        return "Private (RFC 1918)" if ip.version == 4 else "Private / Unique-local"
    if ip.is_global:
        return "Public (globally routable)"
    return "Special-purpose"


def ipv4_class(ip):
    """Legacy classful network class for an IPv4 address (A-E)."""
    first = int(str(ip).split(".")[0])
    if first < 128:
        return "A", "255.0.0.0 (/8)"
    if first < 192:
        return "B", "255.255.0.0 (/16)"
    if first < 224:
        return "C", "255.255.255.0 (/24)"
    if first < 240:
        return "D (Multicast)", "N/A"
    return "E (Experimental)", "N/A"


def to_binary(ip):
    """Dotted binary for IPv4, or grouped hex-expanded form for IPv6."""
    if ip.version == 4:
        return ".".join(f"{int(octet):08b}" for octet in str(ip).split("."))
    return ip.exploded  # full 8-group form, e.g. 2001:0db8:0000:...


def analyze(ip_text):
    """
    Return an ordered dict of offline facts about `ip_text`.
    Raises ValueError if the address is invalid.
    """
    ip = validate_ip(ip_text)
    if ip is None:
        raise ValueError(f"'{ip_text}' is not a valid IPv4 or IPv6 address")

    facts = {
        "Address": str(ip),
        "Version": f"IPv{ip.version}",
        "Type": classify(ip),
        "Reverse DNS name": ip.reverse_pointer,
    }

    if ip.version == 4:
        cls, mask = ipv4_class(ip)
        facts["Binary"] = to_binary(ip)
        facts["Integer value"] = str(int(ip))
        facts["Classful class"] = cls
        facts["Default mask"] = mask
        facts["IPv4-mapped IPv6"] = f"::ffff:{ip}"
    else:
        facts["Expanded form"] = ip.exploded
        facts["Compressed form"] = ip.compressed
        facts["/64 network prefix"] = str(ipaddress.ip_network(f"{ip}/64", strict=False))
        if ip.ipv4_mapped:
            facts["Embedded IPv4"] = str(ip.ipv4_mapped)

    return facts


def subnet_info(cidr_text):
    """
    Subnet calculator: network, broadcast, mask, usable host range and count.
    Accepts e.g. '192.168.10.0/26' or '2001:db8::/48'.
    """
    net = ipaddress.ip_network(cidr_text.strip(), strict=False)
    info = {
        "Network": str(net.network_address),
        "Prefix length": f"/{net.prefixlen}",
        "Total addresses": f"{net.num_addresses:,}",
    }
    if net.version == 4:
        info["Subnet mask"] = str(net.netmask)
        info["Wildcard mask"] = str(net.hostmask)
        info["Broadcast"] = str(net.broadcast_address)
        if net.num_addresses > 2:
            hosts_first = net.network_address + 1
            hosts_last = net.broadcast_address - 1
            info["Usable host range"] = f"{hosts_first} - {hosts_last}"
            info["Usable hosts"] = f"{net.num_addresses - 2:,}"
        else:  # /31 and /32 are special cases (RFC 3021)
            info["Usable host range"] = f"{net[0]} - {net[-1]}"
            info["Usable hosts"] = str(net.num_addresses)
    else:
        info["Last address"] = str(net[-1])
    return info
