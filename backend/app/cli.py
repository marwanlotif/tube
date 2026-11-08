import argparse
import asyncio
import socket
import webbrowser

import uvicorn

from app.core.config import get_config
from app.main import create_app


def find_port(host: str, start: int, attempts: int = 20) -> int:
    for offset in range(attempts):
        port = start + offset
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((host, port))
            except OSError:
                continue
            return port
    raise SystemExit(f"No free port found in range {start}-{start + attempts - 1}")


async def _serve(app, host: str, port: int, open_browser: bool) -> None:
    server = uvicorn.Server(
        uvicorn.Config(app, host=host, port=port, log_level="info", access_log=False)
    )
    task = asyncio.create_task(server.serve())
    while not server.started:
        if task.done():
            return
        await asyncio.sleep(0.1)
    url = f"http://{host}:{port}"
    print(f"\n  Tube running at {url}\n  Press Ctrl+C to stop.\n")
    if open_browser:
        webbrowser.open(url)
    await task


def main() -> None:
    parser = argparse.ArgumentParser(description="Tube local downloader")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    config = get_config()
    host = args.host or config.host
    port = args.port or find_port(host, config.port)
    if not config.frontend_dist.joinpath("index.html").is_file():
        print("Frontend build not found. Run `make build` first.")

    app = create_app(config)
    try:
        asyncio.run(_serve(app, host, port, not args.no_browser))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
