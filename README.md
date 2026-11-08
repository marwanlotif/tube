# Tube

A local video and audio downloader with a small web UI. FastAPI runs the queue and a
React frontend drives it. Files are written straight to disk on this machine — there is no
account, no cloud and no telemetry.

## Requirements

- Linux
- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) and FFmpeg on `PATH`
- Node.js only if you want to rebuild the frontend

```bash
sudo pacman -S yt-dlp ffmpeg     # Arch
sudo apt install yt-dlp ffmpeg   # Debian/Ubuntu
```

## Quick start

```bash
make run       # installs/builds what is missing, opens http://127.0.0.1:8765
```

`make` on its own does the same thing. The build step is skipped when
`frontend/dist` is already newer than the frontend sources, so Node is not needed once a
current build exists.

Useful flags:

```bash
make run ARGS="--port 9000 --no-browser"
```

Configuration comes from environment variables or a `.env` file in the repo root. See
[`.env.example`](.env.example). The data directory (SQLite, thumbnails, logs) defaults to
`~/.local/share/vid-dwn`.

## What it does

- One video at a time, with a configurable worker limit (1–4)
- Server-side format resolution: presets are matched against the streams a video really
  has, then merged into a compatible container (no silent re-encoding)
- Video, audio-only (MP3/M4A/Opus/FLAC/WAV) and optional subtitles
- Live queue progress over one local WebSocket: speed, ETA, cancel, retry
- Resume: canceled or crashed downloads keep their partial file; retry continues it
- Verification: a job is only marked completed when the output file exists inside the
  output directory and is non-empty
- History, stats and storage info in the UI

Output defaults:

| Kind  | Directory          |
| ----- | ------------------ |
| Video | `~/Videos/VidDwn`  |
| Audio | `~/Music/VidDwn`   |

Only directories inside the configured media roots may be used. Folder, filename
template, audio defaults, subtitles, network tuning, browser cookies and concurrency are
editable in Settings.

## Security

Tube binds to localhost. Every mutating API call needs a per-process capability token
injected into the served page, and the WebSocket authenticates with a first message (not
a query string). Host and origin checks reject unexpected callers. The app is not meant
to be exposed through a reverse proxy or to other machines.

## Development

```bash
make test      # pytest + ruff
make lint      # ruff + tsc
make build     # production frontend build
```

Layout:

```
backend/    FastAPI app, domain logic, SQLite repositories, yt-dlp integration
frontend/   React + Vite + Tailwind UI
Makefile    install/build/run; rebuilds the frontend when it is stale
```

Backend tests use a fake `yt-dlp` (`backend/tests/fakes/yt-dlp`) so no network or media
tooling is needed. Run the app against a scratch data dir with:

```bash
VID_DWN_DATA_DIR=/tmp/vid-dwn \
VID_DWN_ALLOWED_MEDIA_ROOTS="$HOME/Videos:$HOME/Music" \
make run ARGS="--no-browser"
```
