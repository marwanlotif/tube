from enum import StrEnum


class Status(StrEnum):
    QUEUED = "queued"
    EXTRACTING = "extracting"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"
    INTERRUPTED = "interrupted"


ACTIVE_STATUSES = {
    Status.QUEUED,
    Status.EXTRACTING,
    Status.DOWNLOADING,
    Status.PROCESSING,
    Status.VERIFYING,
}
TERMINAL_STATUSES = {Status.COMPLETED, Status.FAILED, Status.CANCELED}
RETRYABLE_STATUSES = {Status.FAILED, Status.CANCELED, Status.INTERRUPTED}


class Event(StrEnum):
    START = "start"
    SPAWN = "spawn"
    POSTPROCESS = "postprocess"
    VERIFY = "verify"
    VERIFIED = "verified"
    FAIL = "fail"
    CANCEL = "cancel"
    INTERRUPT = "interrupt"
    RETRY = "retry"


class Mode(StrEnum):
    VIDEO = "video"
    AUDIO = "audio"
