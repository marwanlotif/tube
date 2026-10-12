import asyncio
from pathlib import Path

import pytest

from app.services.storage import kill_process_group


def _gone(pid: int) -> bool:
    try:
        stat = Path(f"/proc/{pid}/stat").read_text()
    except OSError:
        return True
    return stat[stat.rindex(")") + 2] == "Z"


@pytest.mark.skipif(not Path("/proc").is_dir(), reason="Linux /proc required")
async def test_kill_process_group_terminates_children(tmp_path):
    child_file = tmp_path / "child.pid"
    proc = await asyncio.create_subprocess_exec(
        "bash",
        "-c",
        f"bash -c 'sleep 60' & echo $! > {child_file}; wait",
        start_new_session=True,
    )
    for _ in range(100):
        if child_file.exists() and child_file.read_text().strip():
            break
        await asyncio.sleep(0.02)
    child = int(child_file.read_text().strip())

    await kill_process_group(proc.pid, grace=0.5)
    await proc.wait()

    for _ in range(100):
        if _gone(child):
            break
        await asyncio.sleep(0.02)
    assert _gone(child)
