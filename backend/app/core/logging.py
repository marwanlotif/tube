import logging
from logging.handlers import RotatingFileHandler

from app.core.config import Config


def setup_logging(config: Config) -> None:
    root = logging.getLogger()
    if getattr(root, "_vid_dwn_configured", False):
        return
    root._vid_dwn_configured = True  # type: ignore[attr-defined]
    root.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    file_handler = RotatingFileHandler(
        config.logs_dir / "vid-dwn.log", maxBytes=2_000_000, backupCount=3
    )
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)
