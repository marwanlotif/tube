# AGENTS.md

Tube (`vid-dwn`) is a local-only video/audio downloader: FastAPI backend drives
yt-dlp/FFmpeg, React frontend is served from the same process. No accounts, no cloud.

## Commands

```bash
make run                                   # installs/builds what is missing, serves http://127.0.0.1:8765
make run ARGS="--port 9000 --no-browser"   # extra CLI flags
make install                               # backend uv sync + frontend npm ci
make build                                 # production frontend build
make test                                  # pytest + ruff
make lint                                  # ruff + tsc
make clean                                 # remove frontend/dist and caches
```

`make` alone is the same as `make run`. `make run` rebuilds the frontend only when a file
in `frontend/src`, `frontend/index.html`, `vite.config.ts`, `tsconfig.json` or
`package.json` is newer than `frontend/dist/index.html`.

Run against scratch state:

```bash
VID_DWN_DATA_DIR=/tmp/vid-dwn \
VID_DWN_ALLOWED_MEDIA_ROOTS="$HOME/Videos:$HOME/Music" \
make run ARGS="--no-browser"
```

## Layout

```
backend/app/
  main.py            create_app() factory: lifespan wiring, middleware, routers, SPA serving
  cli.py             argparse + uvicorn entry point (`vid-dwn` script)
  core/              config (pydantic-settings), errors, logging, security
  api/routes/        videos, downloads, settings, system, media, ws
  domain/            pure logic: enums, formats/presets, naming templates, progress parsing,
                     state transitions, URL validation (SSRF guard)
  services/          download_manager (workers/queue), runner (subprocess), extractor,
                     events (EventBus), settings, storage (path containment)
  integrations/      ytdlp binary probing and invocation
  db/                SQLAlchemy async engine, tables, repositories
  schemas/           Pydantic request/response models
  tests/             pytest; fake yt-dlp in tests/fakes/yt-dlp
frontend/src/
  api/client.ts      fetch wrapper, token handling, typed methods
  api/types.ts       generated from OpenAPI — do not edit by hand
  api/queries.ts     react-query hooks
  components/        ui primitives + downloads/video/layout components
  pages/             Home, Downloads, Settings
  realtime/          WebSocket provider
```

## Backend conventions

- Python 3.12, ruff with line length 100. Keep domain logic in `app/domain` pure and
  testable; keep subprocess/network side effects in `app/services` or `app/integrations`.
- Configuration is `VID_DWN_*` env vars (or repo-root `.env`), read through
  `app.core.config.Config` / `get_config()`. Add new settings there and document them in
  `.env.example`.
- New API routes: create/extend a router in `app/api/routes/`, register it in
  `create_app()`, use the `AppError` error shape (`{"error": {"code", "message", "details"}}`).
- Downloads run in the `DownloadManager` worker pool, not inside request handlers. Emit
  progress through `EventBus`; WebSocket clients authenticate with a first message, never
  a query string.
- Persist through repositories in `app/db/repos.py`; tables live in `app/db/tables.py`.
- Keep tests offline: they use `backend/tests/fakes/yt-dlp` and a fake FFmpeg path. Add a
  test for any new branch, parser, state transition, or security check.

## Security invariants (do not weaken)

- Bind localhost only; `TrustedHostMiddleware` + origin checks reject unexpected callers.
- Every mutating `/api` request needs the per-process `X-Vid-Dwn-Token` header. The token
  is injected into `index.html` and also available from `GET /api/session`.
- All media paths must stay inside a configured media root (`is_within`); reject arbitrary
  filesystem paths. URL extraction validates the host against private/loopback addresses
  (`assert_public_host`).
- Files only count as completed when they exist inside the output directory and are
  non-empty.

## Frontend conventions

- React 19 + Vite + Tailwind v4 + TanStack Query + React Router. TypeScript is strict and
  checked by `tsc --noEmit` during `npm run build` and `make lint`.
- Add server calls as a method in `src/api/client.ts` and a hook in `src/api/queries.ts`;
  update `src/api/types.ts` with `npm run gen:api` against a running server.
- Reuse the primitives in `src/components/ui` and the existing page/section structure
  instead of new ad-hoc styles.

## Gotchas

- `frontend/dist` is gitignored; `make run` needs Node only when a build is stale/missing.
- The backend serves the SPA for any non-`api/` path, so frontend routing needs no server
  changes.
- One SQLite database lives under `VID_DWN_DATA_DIR` (`vid-dwn.sqlite3`); recovery of
  interrupted jobs runs at startup.
