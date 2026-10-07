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
