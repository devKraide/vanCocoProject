from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SceneId(str, Enum):
    INTRO = "INTRO"
    CROSSROADS = "CROSSROADS"
    RITUAL_GATE = "RITUAL_GATE"
    FINAL_LIGHT = "FINAL_LIGHT"
    FINAL_SHADOW = "FINAL_SHADOW"


class EventType(str, Enum):
    START = "START"
    GESTURE = "GESTURE"
    SYSTEM = "SYSTEM"


class GestureType(str, Enum):
    HAND_OPEN = "HAND_OPEN"
    HAND_CLOSED = "HAND_CLOSED"
    POINT_LEFT = "POINT_LEFT"
    POINT_RIGHT = "POINT_RIGHT"


@dataclass(frozen=True)
class StoryEvent:
    event_type: EventType
    value: str
    source: str
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class AppConfig:
    title: str = "Hand Gesture Narrative Engine"
    intro_video: str = "media/intro.mp4"
    ambient_sound: str = "media/ambient.wav"
    success_sound: str = "media/success.wav"
    failure_sound: str = "media/failure.wav"
    camera_index: int = 0
    min_detection_confidence: float = 0.6
    min_tracking_confidence: float = 0.5
    stable_frames_required: int = 6
    event_cooldown_seconds: float = 1.0
    manual_help: tuple[str, ...] = (
        "start",
        "gesture:HAND_OPEN",
        "gesture:HAND_CLOSED",
        "gesture:POINT_LEFT",
        "gesture:POINT_RIGHT",
        "status",
        "quit",
    )
