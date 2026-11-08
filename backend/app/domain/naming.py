import re

from app.core.errors import AppError

DEFAULT_TEMPLATE = "%(title).200B [%(id)s].%(ext)s"
ALLOWED_TOKENS = {
    "title",
    "id",
    "uploader",
    "upload_date",
    "ext",
    "resolution",
    "playlist_index",
}
TOKEN_RE = re.compile(r"%\(([a-zA-Z_]+)(?::[^)]*)?\)")


def validate_template(template: str) -> str:
    template = (template or "").strip()
    if not template:
        return DEFAULT_TEMPLATE
    if len(template) > 240:
        raise AppError("INVALID_TEMPLATE", "Filename template is too long")
    if any(ch in template for ch in ("/", "\\", "\x00")) or ".." in template:
        raise AppError("INVALID_TEMPLATE", "Filename template cannot contain paths")
    tokens = TOKEN_RE.findall(template)
    unknown = [t for t in tokens if t not in ALLOWED_TOKENS]
    if unknown:
        raise AppError("INVALID_TEMPLATE", f"Unsupported template fields: {', '.join(unknown)}")
    if "ext" not in tokens:
        raise AppError("INVALID_TEMPLATE", "Template must end with %(ext)s")
    if "%" in TOKEN_RE.sub("", template):
        raise AppError("INVALID_TEMPLATE", "Template contains an unsupported placeholder")
    return template


# Characters that are unsafe or awkward in a directory name on common filesystems
# (including FAT/exFAT media), plus path separators.
_UNSAFE_DIR_CHARS = re.compile(r'[/\\:*?"<>|\x00-\x1f\x7f]')
_MAX_DIR_BYTES = 120
PLAYLIST_INDEX_RE = re.compile(r"%\(playlist_index\)([-#0 +]*\d*(?:\.\d+)?[a-zA-Z])")


def _truncate_utf8(value: str, limit: int) -> str:
    encoded = value.encode()
    if len(encoded) <= limit:
        return value
    return encoded[:limit].decode(errors="ignore")


def safe_folder_name(title: str | None, fallback: str | None = None) -> str:
    """A single path component derived from a playlist title, never a path."""
    for candidate in (title, fallback):
        name = _UNSAFE_DIR_CHARS.sub("_", candidate or "")
        name = " ".join(name.split())
        name = _truncate_utf8(name, _MAX_DIR_BYTES).strip(" .")
        if name:
            return name
    return "playlist"


def render_playlist_index(template: str, index: int, count: int) -> str:
    """Fill in ``%(playlist_index)…`` for one item of a playlist downloaded item by item.

    Each item runs as its own yt-dlp job, so yt-dlp itself never knows the position.
    Like yt-dlp, ``%(playlist_index)s`` is zero-padded to the width of the item count.
    """
    width = len(str(max(count, index, 1)))

    def substitute(match: re.Match) -> str:
        spec = match.group(1)
        if spec == "s":
            return str(index).zfill(width)
        try:
            return ("%" + spec) % index
        except (TypeError, ValueError):
            return str(index).zfill(width)

    return PLAYLIST_INDEX_RE.sub(substitute, template)
