from app.domain.enums import Event, Status


class InvalidTransition(Exception):
    def __init__(self, current: Status, event: Event):
        super().__init__(f"cannot apply {event.value} while {current.value}")
        self.current = current
        self.event = event


TRANSITIONS: dict[Status, dict[Event, Status]] = {
    Status.QUEUED: {
        Event.START: Status.EXTRACTING,
        Event.SPAWN: Status.DOWNLOADING,
        Event.FAIL: Status.FAILED,
        Event.CANCEL: Status.CANCELED,
        Event.INTERRUPT: Status.INTERRUPTED,
    },
    Status.EXTRACTING: {
        Event.SPAWN: Status.DOWNLOADING,
        Event.FAIL: Status.FAILED,
        Event.CANCEL: Status.CANCELED,
        Event.INTERRUPT: Status.INTERRUPTED,
    },
    Status.DOWNLOADING: {
        Event.POSTPROCESS: Status.PROCESSING,
        Event.VERIFY: Status.VERIFYING,
        Event.FAIL: Status.FAILED,
        Event.CANCEL: Status.CANCELED,
        Event.INTERRUPT: Status.INTERRUPTED,
    },
    Status.PROCESSING: {
        Event.VERIFY: Status.VERIFYING,
        Event.FAIL: Status.FAILED,
        Event.CANCEL: Status.CANCELED,
        Event.INTERRUPT: Status.INTERRUPTED,
    },
    Status.VERIFYING: {
        Event.VERIFIED: Status.COMPLETED,
        Event.FAIL: Status.FAILED,
        Event.CANCEL: Status.CANCELED,
        Event.INTERRUPT: Status.INTERRUPTED,
    },
    Status.FAILED: {Event.RETRY: Status.QUEUED},
    Status.CANCELED: {Event.RETRY: Status.QUEUED},
    Status.INTERRUPTED: {Event.RETRY: Status.QUEUED},
    Status.COMPLETED: {},
}


def apply(current: Status, event: Event) -> Status:
    try:
        return TRANSITIONS[current][event]
    except KeyError:
        raise InvalidTransition(current, event) from None
