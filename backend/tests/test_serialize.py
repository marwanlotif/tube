import json
from datetime import UTC, datetime

from app.db.tables import DownloadRow
from app.schemas.serialize import download_out


def test_download_out_is_json_serializable_for_websocket_broadcast():
    row = DownloadRow(
        id="job-1",
        url="https://example.com/watch?v=abc",
        mode="video",
        status="failed",
        resumable=False,
        created_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
    )
    payload = download_out(row)
    encoded = json.dumps({"type": "download.updated", "download": payload})
    assert '"created_at"' in encoded
    assert payload["status"] == "failed"
