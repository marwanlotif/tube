import pytest

from app.domain.enums import Event, Status
from app.domain.state import InvalidTransition, apply


def test_happy_path_transitions():
    assert apply(Status.QUEUED, Event.SPAWN) == Status.DOWNLOADING
    assert apply(Status.QUEUED, Event.START) == Status.EXTRACTING
    assert apply(Status.EXTRACTING, Event.SPAWN) == Status.DOWNLOADING
    assert apply(Status.DOWNLOADING, Event.POSTPROCESS) == Status.PROCESSING
    assert apply(Status.PROCESSING, Event.VERIFY) == Status.VERIFYING
    assert apply(Status.VERIFYING, Event.VERIFIED) == Status.COMPLETED
    assert apply(Status.DOWNLOADING, Event.VERIFY) == Status.VERIFYING


def test_retry_paths():
    for status in (Status.FAILED, Status.CANCELED, Status.INTERRUPTED):
        assert apply(status, Event.RETRY) == Status.QUEUED


def test_cancel_and_fail_from_active_states():
    for status in (Status.QUEUED, Status.EXTRACTING, Status.DOWNLOADING,
                   Status.PROCESSING, Status.VERIFYING):
        assert apply(status, Event.CANCEL) == Status.CANCELED
        assert apply(status, Event.FAIL) == Status.FAILED
        assert apply(status, Event.INTERRUPT) == Status.INTERRUPTED


def test_terminal_states_are_terminal():
    with pytest.raises(InvalidTransition):
        apply(Status.COMPLETED, Event.CANCEL)
    with pytest.raises(InvalidTransition):
        apply(Status.COMPLETED, Event.RETRY)
    with pytest.raises(InvalidTransition):
        apply(Status.CANCELED, Event.CANCEL)
