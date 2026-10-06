from app.core.config import Config


def origin_allowed(origin: str | None, host: str, config: Config) -> bool:
    if not origin:
        return True
    allowed = {
        f"http://{host}",
        f"https://{host}",
        *config.dev_origin_list,
    }
    return origin in allowed
