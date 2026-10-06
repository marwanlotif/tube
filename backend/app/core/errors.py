import re

from fastapi import Request
from fastapi.responses import JSONResponse

REDACT_RE = re.compile(r"(?i)\b(token|sig|signature|key|password|auth|expire|ei|ip)=([^&\s]+)")


def redact(text: str) -> str:
    return REDACT_RE.sub(r"\1=[redacted]", text)


class AppError(Exception):
    def __init__(self, code: str, message: str, status: int = 400, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.details = details or {}


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status,
        content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
    )
