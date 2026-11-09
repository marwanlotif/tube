import pytest

from app.core.errors import AppError
from app.domain.urls import normalize_url
from app.services.job_spec import job_options, needs_ffmpeg
from app.services.settings import normalize_settings


@pytest.fixture
def settings(config):
    return normalize_settings({}, config)


def test_job_options_use_settings_by_default(settings):
    options = job_options(settings, mode="video")
    assert options["output_dir"] == settings.video_dir
    assert options["audio_format"] == settings.audio.format
    assert options["subtitles"] == settings.subtitles.model_dump()
    assert options["filename_template"] == settings.filename_template


def test_job_options_apply_overrides(settings):
    options = job_options(
        settings, mode="audio", audio_format="flac", subtitles=True, subtitle_langs=" en,de "
    )
    assert options["output_dir"] == settings.audio_dir
    assert options["audio_format"] == "flac"
    assert options["subtitles"]["enabled"] is True
    assert options["subtitles"]["langs"] == "en,de"


def test_job_options_reject_bad_subtitle_languages(settings):
    with pytest.raises(AppError) as exc:
        job_options(settings, mode="video", subtitles=True, subtitle_langs="en;rm -rf")
    assert exc.value.code == "INVALID_SETTINGS"


def test_needs_ffmpeg(settings):
    video = job_options(settings, mode="video")
    assert needs_ffmpeg(video, requires_merge=False) is False
    assert needs_ffmpeg(video, requires_merge=True) is True
    assert needs_ffmpeg(job_options(settings, mode="audio"), requires_merge=False) is True


def test_normalize_url_checks_syntax_without_resolving():
    assert normalize_url(" https://example.com/a?b=1#c ") == "https://example.com/a?b=1"
    assert normalize_url("http://example.com") == "http://example.com/"
    for bad in ("ftp://x.test/a", "https://user:pw@x.test/", "https:///nohost", ""):
        with pytest.raises(AppError):
            normalize_url(bad)
