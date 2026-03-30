from __future__ import annotations

from dataclasses import dataclass, field

from config import GestureType, SceneId, StoryEvent


@dataclass
class GameState:
    current_scene: SceneId = SceneId.INTRO
    event_history: list[StoryEvent] = field(default_factory=list)
    gesture_history: list[GestureType] = field(default_factory=list)
    discovered_clues: set[str] = field(default_factory=set)
    choices: dict[str, str] = field(default_factory=dict)
    flags: dict[str, bool] = field(
        default_factory=lambda: {
            "story_started": False,
            "ritual_ready": False,
        }
    )


class StateManager:
    """Centraliza o estado global da narrativa."""

    def __init__(self) -> None:
        self._state = GameState()

    @property
    def state(self) -> GameState:
        return self._state

    def record_event(self, event: StoryEvent) -> None:
        self._state.event_history.append(event)
        if event.value in GestureType._value2member_map_:
            self._state.gesture_history.append(GestureType(event.value))

    def move_to(self, scene_id: SceneId) -> None:
        self._state.current_scene = scene_id

    def add_clue(self, clue: str) -> None:
        self._state.discovered_clues.add(clue)

    def has_clue(self, clue: str) -> bool:
        return clue in self._state.discovered_clues

    def set_choice(self, key: str, value: str) -> None:
        self._state.choices[key] = value

    def get_choice(self, key: str) -> str | None:
        return self._state.choices.get(key)

    def set_flag(self, key: str, value: bool = True) -> None:
        self._state.flags[key] = value

    def get_flag(self, key: str) -> bool:
        return self._state.flags.get(key, False)

    def is_terminal(self) -> bool:
        return self._state.current_scene in {SceneId.FINAL_LIGHT, SceneId.FINAL_SHADOW}

    def snapshot(self) -> dict[str, object]:
        return {
            "scene": self._state.current_scene.value,
            "choices": dict(self._state.choices),
            "flags": dict(self._state.flags),
            "clues": sorted(self._state.discovered_clues),
            "gesture_history": [gesture.value for gesture in self._state.gesture_history],
        }
