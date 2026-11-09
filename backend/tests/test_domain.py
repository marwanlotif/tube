import socket

import pytest

from app.core.errors import AppError
from app.domain.naming import DEFAULT_TEMPLATE, validate_template
from app.domain.urls import validate_url
from app.integrations.ytdlp import info_argv


def public_resolver(*args, **kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]


def private_resolver(*args, **kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0))]


def test_accepts_public_https():
    assert validate_url("https://example.com/watch?v=abc#frag", public_resolver) == (
        "https://example.com/watch?v=abc"
    )


def test_rejects_non_http_schemes():
    for url in ("file:///etc/passwd", "ftp://example.com/x", "javascript:alert(1)"):
        with pytest.raises(AppError):
            validate_url(url, public_resolver)


def test_rejects_private_and_loopback_hosts():
    with pytest.raises(AppError):
        validate_url("http://127.0.0.1:8080/x", private_resolver)
    with pytest.raises(AppError):
        validate_url("http://localhost/x", public_resolver)
    with pytest.raises(AppError):
        validate_url("http://user:pass@example.com/x", public_resolver)


def test_template_accepts_default_and_rejects_paths():
    assert validate_template(DEFAULT_TEMPLATE) == DEFAULT_TEMPLATE
    assert validate_template("%(uploader)s - %(title)s.%(ext)s")


@pytest.mark.parametrize(
    "template",
    ["../evil.%(ext)s", "sub/dir.%(ext)s", "%(title)s", "%(unknown)s.%(ext)s",
     "100%.%(ext)s"],
)
def test_template_rejects_unsafe_values(template):
    with pytest.raises(AppError):
        validate_template(template)


def test_info_argv_adds_cookies_only_when_configured():
    plain = info_argv("yt-dlp", "https://example.com/v")
    assert "--cookies-from-browser" not in plain
    assert plain[-1] == "https://example.com/v"

    signed_in = info_argv("yt-dlp", "https://example.com/v", "firefox")
    index = signed_in.index("--cookies-from-browser")
    assert signed_in[index + 1] == "firefox"
    assert signed_in[-1] == "https://example.com/v"
