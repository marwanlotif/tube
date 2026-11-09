import ipaddress
import socket
from urllib.parse import parse_qs, urlsplit, urlunsplit

from app.core.errors import AppError

MAX_URL_LENGTH = 2048


def _ip_is_blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def assert_public_host(hostname: str, resolver=socket.getaddrinfo) -> None:
    if not hostname:
        raise AppError("INVALID_URL", "URL has no hostname")
    lowered = hostname.lower()
    if lowered in {"localhost", "localhost.localdomain"} or lowered.endswith(".local"):
        raise AppError("INVALID_URL", "Local hostnames are not allowed")
    try:
        infos = resolver(hostname, None, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise AppError("INVALID_URL", f"Cannot resolve host: {exc}") from exc
    for info in infos:
        address = info[4][0]
        try:
            ip = ipaddress.ip_address(address.split("%")[0])
        except ValueError:
            continue
        if _ip_is_blocked(ip):
            raise AppError("INVALID_URL", "Private or local addresses are not allowed")


def looks_like_playlist_member(url: str) -> bool:
    """A link to one video that also names a playlist.

    YouTube puts the video in the query (``watch?v=…&list=…``) or, for ``youtu.be`` short
    links, in the path (``youtu.be/<id>?list=…``).
    """
    parts = urlsplit(url)
    query = parse_qs(parts.query)
    if not query.get("list"):
        return False
    if query.get("v"):
        return True
    return (parts.hostname or "").lower() == "youtu.be" and bool(parts.path.strip("/"))


def validate_url(raw: str, resolver=socket.getaddrinfo) -> str:
    raw = (raw or "").strip()
    if not raw or len(raw) > MAX_URL_LENGTH:
        raise AppError("INVALID_URL", "Enter a valid URL")
    parts = urlsplit(raw)
    if parts.scheme not in {"http", "https"}:
        raise AppError("INVALID_URL", "Only http and https URLs are supported")
    if parts.username or parts.password:
        raise AppError("INVALID_URL", "URLs with credentials are not supported")
    assert_public_host(parts.hostname or "", resolver)
    return urlunsplit((parts.scheme, parts.netloc, parts.path or "/", parts.query, ""))
