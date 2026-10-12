import json
from pathlib import Path

import pytest

from app.core.errors import AppError
from app.domain.formats import (
    parse_formats,
    resolve_custom,
    resolve_preset,
)
from app.domain.progress import parse_line


def load_formats():
    raw = json.loads((Path(__file__).parent / "fakes/info.json").read_text())
    return parse_formats(raw["formats"])


def test_parse_skips_storyboards_and_classifies():
    options = parse_formats(
        [
            {"format_id": "1", "ext": "mp4", "vcodec": "avc1", "acodec": "none",
             "height": 720},
            {"format_id": "2", "ext": "m4a", "vcodec": "none", "acodec": "mp4a", "abr": 128},
            {"format_id": "3", "ext": "mp4", "vcodec": "avc1", "acodec": "mp4a", "height": 360},
            {"format_id": "4", "ext": "mhtml", "vcodec": "none", "acodec": "none"},
        ]
    )
    assert [f.kind for f in options] == ["video", "audio", "combined"]


def test_1080_preset_prefers_h264_and_aac():
    resolved = resolve_preset(load_formats(), "best_1080")
    assert resolved.selector == "137+140"
    assert resolved.container == "mp4"
    assert resolved.requires_merge
    assert resolved.estimated_bytes == 6_000_000


def test_audio_preset_and_webm():
    options = load_formats()
    audio = resolve_preset(options, "audio")
    assert audio.selector == "251"
    assert audio.vcodec is None
    webm = resolve_preset(options, "webm_1080")
    assert webm.selector == "248+251"
    assert webm.container == "webm"


def test_best_quality_switches_container_to_mkv_when_incompatible():
    resolved = resolve_preset(load_formats(), "best_quality")
    assert resolved.video_id == "137"
    assert resolved.audio_id == "251"
    assert resolved.container == "mkv"


def test_custom_selection_and_stale_ids():
    options = load_formats()
    resolved = resolve_custom(options, "18", None)
    assert resolved.container == "mp4"
    assert not resolved.requires_merge
    with pytest.raises(AppError) as exc:
        resolve_custom(options, "999", None)
    assert exc.value.code == "FORMAT_STALE"


def test_progress_line_parsing():
    line = (
        'PROGRESS {"status":"downloading","downloaded_bytes":50,"total_bytes":200,'
        '"speed":1000,"eta":3}'
    )
    parsed = parse_line(line)
    assert parsed.kind == "progress"
    assert parsed.progress.percent == 25.0
    assert parsed.progress.eta == 3


def test_progress_handles_missing_fields_and_paths():
    parsed = parse_line('PROGRESS {"status":"downloading","downloaded_bytes":null}')
    assert parsed.progress.downloaded_bytes == 0
    assert parsed.progress.percent is None
    assert parse_line("DEST /tmp/a.mp4").path == "/tmp/a.mp4"
    assert parse_line("FINAL /tmp/a.mp4").kind == "final"
    assert parse_line("unrelated noise") is None
