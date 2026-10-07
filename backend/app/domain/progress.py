import json
from dataclasses import dataclass


@dataclass(frozen=True)
class ProgressUpdate:
    status: str
    downloaded_bytes: int
    total_bytes: int | None
    speed: float | None
    eta: int | None
    percent: float | None


@dataclass(frozen=True)
class ParsedLine:
    kind: str  # progress | dest | final
    progress: ProgressUpdate | None = None
    path: str | None = None


def _as_int(value) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _as_float(value) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def parse_progress(payload: dict) -> ProgressUpdate:
    total = _as_int(payload.get("total_bytes")) or _as_int(
        payload.get("total_bytes_estimate")
    )
    downloaded = _as_int(payload.get("downloaded_bytes")) or 0
    percent = None
    if total and total > 0:
        percent = min(100.0, max(0.0, downloaded / total * 100))
    return ProgressUpdate(
        status=str(payload.get("status") or "downloading"),
        downloaded_bytes=downloaded,
        total_bytes=total,
        speed=_as_float(payload.get("speed")),
        eta=_as_int(payload.get("eta")),
        percent=percent,
    )


def parse_line(line: str) -> ParsedLine | None:
    line = line.strip()
    if line.startswith("PROGRESS "):
        try:
            payload = json.loads(line[len("PROGRESS ") :])
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None
        return ParsedLine(kind="progress", progress=parse_progress(payload))
    if line.startswith("DEST "):
        return ParsedLine(kind="dest", path=line[len("DEST ") :].strip())
    if line.startswith("FINAL "):
        return ParsedLine(kind="final", path=line[len("FINAL ") :].strip())
    return None
