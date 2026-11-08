import socket

import pytest

from app.core.errors import AppError
from app.domain.naming import (
    DEFAULT_TEMPLATE,
    render_playlist_index,
    safe_folder_name,
    validate_template,
)
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


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("My Playlist", "My Playlist"),
        ("a/b\\c", "a_b_c"),
        ("../../etc", "_.._etc"),
        ("..", "fallback-id"),
        ("  . spaced  out .  ", "spaced out"),
        ("tab\there\nnewline\x00nul", "tab_here_newline_nul"),
        ('what? *really* <yes> "no" | c:', "what_ _really_ _yes_ _no_ _ c_"),
        ("", "fallback-id"),
        (None, "fallback-id"),
    ],
)
def test_safe_folder_name_yields_a_single_component(title, expected):
    name = safe_folder_name(title, "fallback-id")
    assert name == expected
    assert "/" not in name and "\\" not in name and name not in {".", ".."}


def test_safe_folder_name_falls_back_to_literal_and_limits_bytes():
    assert safe_folder_name("...", "///") == "___"
    assert safe_folder_name(None, None) == "playlist"
    long = safe_folder_name("é" * 200)
    assert len(long.encode()) <= 120
    assert long == "é" * 60  # never splits a multi-byte character


@pytest.mark.parametrize(
    ("template", "index", "count", "expected"),
    [
        ("%(playlist_index)s - %(title)s.%(ext)s", 7, 15, "07 - %(title)s.%(ext)s"),
        ("%(playlist_index)s - %(title)s.%(ext)s", 7, 9, "7 - %(title)s.%(ext)s"),
        ("%(playlist_index)03d %(title)s.%(ext)s", 7, 15, "007 %(title)s.%(ext)s"),
        ("%(playlist_index)d.%(ext)s", 120, 15, "120.%(ext)s"),
        ("%(title)s.%(ext)s", 3, 10, "%(title)s.%(ext)s"),
    ],
)
def test_render_playlist_index(template, index, count, expected):
    rendered = render_playlist_index(template, index, count)
    assert rendered == expected
    validate_template(rendered)  # the result is still an acceptable template
