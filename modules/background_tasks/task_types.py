from __future__ import annotations

from enum import Enum


class TaskType(str, Enum):
    DOWNLOAD_VIDEO = "DOWNLOAD_VIDEO"
    DOWNLOAD_MODEL = "DOWNLOAD_MODEL"
    VIDEO_ANALYSIS = "VIDEO_ANALYSIS"
    CLIP_RENDER = "CLIP_RENDER"
    RUNTIME_UPDATE = "RUNTIME_UPDATE"


class TaskStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"

