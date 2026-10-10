import asyncio
import logging
from dataclasses import dataclass, field

from app.core.errors import redact
from app.integrations.ytdlp import describe_command, download_argv
from app.services.storage import read_pid_start_ticks

log = logging.getLogger(__name__)


@dataclass
class RunHandle:
    proc: asyncio.subprocess.Process
    argv: list[str]
    pid_started_ticks: int | None = None
    stderr_tail: str = ""
    dest_path: str | None = None
    final_path: str | None = None
    _stderr_parts: list[str] = field(default_factory=list)

    @property
    def pid(self) -> int:
        return self.proc.pid

    async def pump_stderr(self) -> None:
        assert self.proc.stderr is not None
        while True:
            chunk = await self.proc.stderr.readline()
            if not chunk:
                break
            self._stderr_parts.append(chunk.decode(errors="replace"))
            total = sum(len(p) for p in self._stderr_parts)
            while total > 8192 and len(self._stderr_parts) > 1:
                total -= len(self._stderr_parts.pop(0))
        self.stderr_tail = redact("".join(self._stderr_parts).strip())


class Runner:
    def __init__(self, binary: str, ffmpeg: str | None):
        self.binary = binary
        self.ffmpeg = ffmpeg

    async def start(self, spec: dict, job_id: str) -> RunHandle:
        argv = download_argv(self.binary, self.ffmpeg, spec)
        log.info("spawn %s", describe_command(argv))
        import os

        env = {**os.environ, "VID_DWN_JOB_ID": job_id}
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=True,
            env=env,
        )
        return RunHandle(
            proc=proc,
            argv=argv,
            pid_started_ticks=read_pid_start_ticks(proc.pid),
        )
