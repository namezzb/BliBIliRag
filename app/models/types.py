from enum import StrEnum


class TaskStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SubtitleSource(StrEnum):
    BILIBILI = "bilibili"
    ASR_DIRECT = "asr_direct"
    ASR_LOCAL = "asr_local"
    FALLBACK = "fallback"


class SummaryType(StrEnum):
    VIDEO = "video"
    SEGMENT = "segment"
    KEYPOINT = "keypoint"

