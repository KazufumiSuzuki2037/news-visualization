"""Shared URL and article eligibility rules for news research."""

import ipaddress
import posixpath
import socket
from urllib.parse import unquote, urlsplit, urlunsplit


def _parts(value):
    if not isinstance(value, str):
        raise ValueError("Invalid public URL")
    try:
        parts = urlsplit(value)
        port = parts.port
    except ValueError as error:
        raise ValueError("Invalid public URL") from error
    if (parts.scheme.lower() != "https" or not parts.hostname or parts.username or parts.password
            or port not in (None, 443) or parts.hostname.endswith(".") or "%" in parts.hostname):
        raise ValueError("Invalid public URL")
    return parts


def normalize_public_url(value):
    """Normalize a public HTTPS URL without a network lookup."""
    parts = _parts(value)
    host = parts.hostname.lower()
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        if not address.is_global:
            raise ValueError("Private address")
    netloc = host if parts.port is None else f"{host}:443"
    if ":" in host and not host.startswith("["):
        netloc = f"[{host}]" + (":443" if parts.port is not None else "")
    return urlunsplit(("https", netloc, parts.path or "/", parts.query, ""))


def public_addresses(value):
    """Resolve once; every returned address must be publicly routable."""
    host = urlsplit(normalize_public_url(value)).hostname
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
    except OSError as error:
        raise ValueError("Cannot resolve public URL") from error
    if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise ValueError("Private address")
    return sorted(addresses)


def validate_public_url(value):
    """Return a normalized HTTPS URL after public DNS/IP validation."""
    normalized = normalize_public_url(value)
    public_addresses(normalized)
    return normalized


def article_eligible(url, language, sites):
    """Registered site articles may use any language; others require confirmed ja."""
    try:
        article = urlsplit(normalize_public_url(url))
    except ValueError:
        return False
    for site in sites:
        if site.get("active") is False:
            continue
        try:
            registered = urlsplit(normalize_public_url(site["url"]))
        except (KeyError, TypeError, ValueError):
            continue
        base_path = posixpath.normpath(unquote(registered.path))
        article_path = posixpath.normpath(unquote(article.path))
        if article.hostname == registered.hostname and (base_path == "/" or article_path == base_path or article_path.startswith(base_path + "/")):
            return True
    return language == "ja"
