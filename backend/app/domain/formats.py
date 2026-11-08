from dataclasses import dataclass

from app.core.errors import AppError

VIDEO_H264 = ("avc1", "h264", "avc")
AUDIO_AAC = ("mp4a", "aac")
CONTAINER_MP4 = {"mp4", "m4a", "m4v"}
CONTAINER_WEBM = {"webm", "weba"}


@dataclass(frozen=True)
class FormatOption:
    format_id: str
    ext: str
    vcodec: str | None
    acodec: str | None
    width: int | None
    height: int | None
    fps: float | None
    tbr: float | None
    abr: float | None
    filesize: int | None
    hdr: bool
    kind: str  # video | audio | combined

    @property
    def estimated_bytes(self) -> int | None:
        return self.filesize

    @property
    def label(self) -> str:
        if self.kind == "audio":
            return f"Audio {self.ext.upper()} {int(self.abr or self.tbr or 0)}kbps"
        height = f"{self.height}p" if self.height else self.ext.upper()
        fps = f"{int(self.fps)}fps" if self.fps and self.fps > 30 else ""
        return " · ".join(p for p in (height, fps, _codec_name(self.vcodec)) if p)


@dataclass(frozen=True)
class ResolvedSelection:
    selector: str
    container: str
    requires_merge: bool
    video_id: str | None
    audio_id: str | None
    label: str
    height: int | None
    fps: float | None
    vcodec: str | None
    acodec: str | None
    estimated_bytes: int | None


def _codec_name(codec: str | None) -> str:
    if not codec or codec == "none":
        return ""
    c = codec.lower()
    if c.startswith(("avc", "h264")):
        return "H.264"
    if c.startswith(("hev", "hvc", "h265")):
        return "H.265"
    if c.startswith("av01"):
        return "AV1"
    if c.startswith("vp9"):
        return "VP9"
    if c.startswith("vp8"):
        return "VP8"
    if c.startswith(("mp4a", "aac")):
        return "AAC"
    if c.startswith("opus"):
        return "Opus"
    if c.startswith("vorbis"):
        return "Vorbis"
    return codec.split(".")[0]


def _size(fmt: dict) -> int | None:
    value = fmt.get("filesize") or fmt.get("filesize_approx")
    return int(value) if value else None


def parse_formats(raw_formats: list[dict]) -> list[FormatOption]:
    options: list[FormatOption] = []
    for fmt in raw_formats or []:
        if fmt.get("ext") in {"mhtml", "none"} or fmt.get("has_drm"):
            continue
        vcodec = fmt.get("vcodec") or "none"
        acodec = fmt.get("acodec") or "none"
        if vcodec == "none" and acodec == "none":
            continue
        if vcodec != "none" and acodec != "none":
            kind = "combined"
        elif vcodec != "none":
            kind = "video"
        else:
            kind = "audio"
        dynamic_range = fmt.get("dynamic_range")
        options.append(
            FormatOption(
                format_id=str(fmt.get("format_id")),
                ext=str(fmt.get("ext") or ""),
                vcodec=None if vcodec == "none" else vcodec,
                acodec=None if acodec == "none" else acodec,
                width=fmt.get("width"),
                height=fmt.get("height"),
                fps=fmt.get("fps"),
                tbr=fmt.get("tbr"),
                abr=fmt.get("abr"),
                filesize=_size(fmt),
                hdr=bool(dynamic_range and str(dynamic_range).upper() not in {"SDR", "NONE"}),
                kind=kind,
            )
        )
    return options


def _is_h264(option: FormatOption) -> bool:
    return bool(option.vcodec and option.vcodec.lower().startswith(VIDEO_H264))


def _is_aac(option: FormatOption) -> bool:
    return bool(option.acodec and option.acodec.lower().startswith(AUDIO_AAC))


def _is_vp9_or_av1(option: FormatOption) -> bool:
    codec = (option.vcodec or "").lower()
    return codec.startswith(("vp9", "vp09", "av01"))


def _is_opus(option: FormatOption) -> bool:
    return (option.acodec or "").lower().startswith("opus")


def _container_for(video: FormatOption, audio: FormatOption | None) -> str:
    if audio is None:
        return video.ext
    if video.ext in CONTAINER_MP4 and audio.ext in CONTAINER_MP4:
        return "mp4"
    if video.ext in CONTAINER_WEBM and audio.ext in CONTAINER_WEBM:
        return "webm"
    return "mkv"


def _best_video(videos: list[FormatOption], cap: int | None, prefer_h264: bool) -> FormatOption | None:
    pool = [v for v in videos if cap is None or (v.height or 0) <= cap]
    if not pool:
        return None
    if prefer_h264:
        h264 = [v for v in pool if _is_h264(v)]
        if h264:
            pool = h264
    return max(pool, key=lambda v: ((v.height or 0), (v.tbr or 0), (v.fps or 0)))


def _best_audio(audios: list[FormatOption], prefer_aac: bool) -> FormatOption | None:
    if not audios:
        return None
    pool = audios
    if prefer_aac:
        aac = [a for a in audios if _is_aac(a)]
        if aac:
            pool = aac
    return max(pool, key=lambda a: (a.abr or a.tbr or 0))


def _best_combined(
    combined: list[FormatOption], cap: int | None, prefer_h264: bool
) -> FormatOption | None:
    pool = [c for c in combined if cap is None or (c.height or 0) <= cap]
    if not pool:
        return None
    if prefer_h264:
        h264 = [c for c in pool if _is_h264(c)]
        if h264:
            pool = h264
    return max(pool, key=lambda c: ((c.height or 0), (c.tbr or 0)))


def _resolve_pair(video: FormatOption, audio: FormatOption | None) -> ResolvedSelection:
    if audio is None:
        return ResolvedSelection(
            selector=video.format_id,
            container=video.ext,
            requires_merge=False,
            video_id=video.format_id,
            audio_id=None,
            label=video.label,
            height=video.height,
            fps=video.fps,
            vcodec=video.vcodec,
            acodec=video.acodec,
            estimated_bytes=video.estimated_bytes,
        )
    size = None
    if video.estimated_bytes and audio.estimated_bytes:
        size = video.estimated_bytes + audio.estimated_bytes
    return ResolvedSelection(
        selector=f"{video.format_id}+{audio.format_id}",
        container=_container_for(video, audio),
        requires_merge=True,
        video_id=video.format_id,
        audio_id=audio.format_id,
        label=f"{video.label} + {_codec_name(audio.acodec)}",
        height=video.height,
        fps=video.fps,
        vcodec=video.vcodec,
        acodec=audio.acodec,
        estimated_bytes=size,
    )


def resolve_preset(options: list[FormatOption], key: str) -> ResolvedSelection | None:
    videos = [f for f in options if f.kind == "video"]
    audios = [f for f in options if f.kind == "audio"]
    combined = [f for f in options if f.kind == "combined"]

    if key == "audio":
        audio = _best_audio(audios, prefer_aac=False)
        if audio is None:
            return None
        return ResolvedSelection(
            selector=audio.format_id,
            container=audio.ext,
            requires_merge=False,
            video_id=None,
            audio_id=audio.format_id,
            label=audio.label,
            height=None,
            fps=None,
            vcodec=None,
            acodec=audio.acodec,
            estimated_bytes=audio.estimated_bytes,
        )

    if key == "best_quality":
        video = _best_video(videos, None, prefer_h264=False)
        audio = _best_audio(audios, prefer_aac=False)
        if video:
            return _resolve_pair(video, audio)
        best = _best_combined(combined, None, prefer_h264=False)
        return _resolve_pair(best, None) if best else None

    if key == "webm_1080":
        vp = [v for v in videos if _is_vp9_or_av1(v) and (v.height or 0) <= 1080]
        if not vp:
            return None
        video = max(vp, key=lambda v: ((v.height or 0), (v.tbr or 0)))
        opus = [a for a in audios if _is_opus(a) and a.ext in CONTAINER_WEBM]
        audio = max(opus, key=lambda a: (a.abr or a.tbr or 0)) if opus else None
        return _resolve_pair(video, audio)

    heights = {"best_2160": 2160, "best_1440": 1440, "best_1080": 1080,
               "best_720": 720, "best_480": 480}
    cap = heights.get(key)
    if cap is None:
        raise AppError("INVALID_PRESET", f"Unknown preset: {key}")

    video = _best_video(videos, cap, prefer_h264=True)
    if video:
        return _resolve_pair(video, _best_audio(audios, prefer_aac=True))
    combined_best = _best_combined(combined, cap, prefer_h264=True)
    if combined_best:
        return _resolve_pair(combined_best, None)
    return None


def resolve_custom(
    options: list[FormatOption], video_id: str, audio_id: str | None
) -> ResolvedSelection:
    by_id = {f.format_id: f for f in options}
    video = by_id.get(video_id)
    if video is None:
        raise AppError("FORMAT_STALE", "Selected format is no longer available")
    if video.kind == "audio":
        raise AppError("INVALID_SELECTION", "Selected format is audio-only")
    if audio_id:
        if video.kind == "combined":
            raise AppError("INVALID_SELECTION", "A combined format cannot be paired with audio")
        audio = by_id.get(audio_id)
        if audio is None or audio.kind != "audio":
            raise AppError("INVALID_SELECTION", "Selected audio format is invalid")
        return _resolve_pair(video, audio)
    if video.kind == "video":
        best_audio = _best_audio([f for f in options if f.kind == "audio"], prefer_aac=True)
        return _resolve_pair(video, best_audio)
    return _resolve_pair(video, None)


PRESET_LABELS = {
    "best_2160": "Up to 4K",
    "best_1440": "Up to 1440p",
    "best_1080": "Up to 1080p",
    "best_720": "Up to 720p",
    "best_480": "Up to 480p",
    "best_quality": "Best quality",
    "webm_1080": "WebM up to 1080p",
    "audio": "Audio only",
}
PRESET_KEYS = list(PRESET_LABELS)


def preset_choices() -> list[dict]:
    """Presets offered before any formats are known, e.g. for a whole playlist.

    Each item resolves its preset when its job runs; "up to" presets fall back to the best
    lower resolution, so they are all offered as available.
    """
    return [{"key": key, "label": label, "available": True} for key, label in PRESET_LABELS.items()]


def preset_list(options: list[FormatOption]) -> list[dict]:
    result = []
    for key in PRESET_KEYS:
        resolved = resolve_preset(options, key)
        result.append(
            {
                "key": key,
                "label": PRESET_LABELS[key],
                "available": resolved is not None,
                "container": resolved.container if resolved else None,
                "height": resolved.height if resolved else None,
                "fps": resolved.fps if resolved else None,
                "vcodec": resolved.vcodec if resolved else None,
                "acodec": resolved.acodec if resolved else None,
                "requires_merge": resolved.requires_merge if resolved else False,
                "estimated_bytes": resolved.estimated_bytes if resolved else None,
                "selector_label": resolved.label if resolved else None,
            }
        )
    return result
