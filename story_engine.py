from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from config import AppConfig, EventType, GestureType, SceneId, StoryEvent
from media_controller import MediaController
from robot_comm import RobotComm
from state_manager import StateManager

Condition = Callable[[StoryEvent, StateManager], bool]
Action = Callable[[StoryEvent, StateManager, MediaController, RobotComm, AppConfig], None]


@dataclass(frozen=True)
class Transition:
    target_scene: SceneId
    condition: Condition
    action: Action | None = None


@dataclass(frozen=True)
class SceneDefinition:
    scene_id: SceneId
    description: str
    on_enter: Action | None = None
    transitions: tuple[Transition, ...] = field(default_factory=tuple)


class StoryEngine:
    """Processa eventos e avanca a narrativa por cenas."""

    def __init__(
        self,
        state_manager: StateManager,
        media_controller: MediaController,
        robot_comm: RobotComm,
        config: AppConfig | None = None,
    ) -> None:
        self.state_manager = state_manager
        self.media_controller = media_controller
        self.robot_comm = robot_comm
        self.config = config or AppConfig()
        self.scenes = self._build_scenes()

    def start(self) -> None:
        self._enter_scene(self.state_manager.state.current_scene)

    def process_event(self, event: StoryEvent) -> SceneId:
        self.state_manager.record_event(event)
        current_scene = self.state_manager.state.current_scene
        scene = self.scenes[current_scene]

        for transition in scene.transitions:
            if transition.condition(event, self.state_manager):
                if transition.action:
                    transition.action(
                        event,
                        self.state_manager,
                        self.media_controller,
                        self.robot_comm,
                        self.config,
                    )
                if transition.target_scene != current_scene:
                    self.state_manager.move_to(transition.target_scene)
                    self._enter_scene(transition.target_scene)
                return transition.target_scene

        self._handle_unmatched_event(event)
        return current_scene

    def _enter_scene(self, scene_id: SceneId) -> None:
        scene = self.scenes[scene_id]
        print(f"\n[SCENE] {scene.scene_id.value} :: {scene.description}")
        if scene.on_enter:
            scene.on_enter(
                StoryEvent(EventType.SYSTEM, "ENTER_SCENE", "engine"),
                self.state_manager,
                self.media_controller,
                self.robot_comm,
                self.config,
            )

    def _handle_unmatched_event(self, event: StoryEvent) -> None:
        self.media_controller.speak(
            f"O gesto '{event.value}' nao altera a narrativa nesta cena."
        )

    def _build_scenes(self) -> dict[SceneId, SceneDefinition]:
        return {
            SceneId.INTRO: SceneDefinition(
                scene_id=SceneId.INTRO,
                description="A historia aguarda o despertar do ritual.",
                on_enter=self._enter_intro,
                transitions=(
                    Transition(SceneId.CROSSROADS, self._is_start_event, self._start_story),
                    Transition(
                        SceneId.CROSSROADS,
                        self._gesture_is(GestureType.HAND_OPEN),
                        self._start_story_from_gesture,
                    ),
                ),
            ),
            SceneId.CROSSROADS: SceneDefinition(
                scene_id=SceneId.CROSSROADS,
                description="A mao do publico define o tom da jornada.",
                on_enter=self._enter_crossroads,
                transitions=(
                    Transition(SceneId.RITUAL_GATE, self._gesture_is(GestureType.HAND_OPEN), self._choose_light_path),
                    Transition(SceneId.RITUAL_GATE, self._gesture_is(GestureType.HAND_CLOSED), self._choose_shadow_path),
                ),
            ),
            SceneId.RITUAL_GATE: SceneDefinition(
                scene_id=SceneId.RITUAL_GATE,
                description="O portal final reage a direcao indicada pela mao.",
                on_enter=self._enter_ritual_gate,
                transitions=(
                    Transition(SceneId.FINAL_LIGHT, self._light_ending_condition, self._play_light_ending),
                    Transition(SceneId.FINAL_SHADOW, self._shadow_ending_condition, self._play_shadow_ending),
                ),
            ),
            SceneId.FINAL_LIGHT: SceneDefinition(
                scene_id=SceneId.FINAL_LIGHT,
                description="O palco responde com um final de reconciliacao.",
                on_enter=self._enter_final_light,
            ),
            SceneId.FINAL_SHADOW: SceneDefinition(
                scene_id=SceneId.FINAL_SHADOW,
                description="O palco mergulha em um final de ruptura e misterio.",
                on_enter=self._enter_final_shadow,
            ),
        }

    @staticmethod
    def _is_start_event(event: StoryEvent, _: StateManager) -> bool:
        return event.event_type == EventType.START

    @staticmethod
    def _gesture_is(gesture: GestureType) -> Condition:
        def matcher(event: StoryEvent, _: StateManager) -> bool:
            return event.event_type == EventType.GESTURE and event.value == gesture.value

        return matcher

    @staticmethod
    def _light_ending_condition(event: StoryEvent, state_manager: StateManager) -> bool:
        selected_path = state_manager.get_choice("path")
        return event.event_type == EventType.GESTURE and (
            (selected_path == "light" and event.value == GestureType.POINT_RIGHT.value)
            or (selected_path == "shadow" and event.value == GestureType.POINT_LEFT.value)
        )

    @staticmethod
    def _shadow_ending_condition(event: StoryEvent, state_manager: StateManager) -> bool:
        selected_path = state_manager.get_choice("path")
        return event.event_type == EventType.GESTURE and (
            (selected_path == "light" and event.value == GestureType.POINT_LEFT.value)
            or (selected_path == "shadow" and event.value == GestureType.POINT_RIGHT.value)
        )

    @staticmethod
    def _enter_intro(
        _: StoryEvent,
        __: StateManager,
        media: MediaController,
        robot: RobotComm,
        config: AppConfig,
    ) -> None:
        media.play_video(config.intro_video)
        media.speak("Use 'start' para iniciar a narrativa.")
        robot.send_command("stage_left", "idle_glow", color="white")

    @staticmethod
    def _start_story(
        _: StoryEvent,
        state_manager: StateManager,
        media: MediaController,
        robot: RobotComm,
        config: AppConfig,
    ) -> None:
        state_manager.set_flag("story_started", True)
        media.play_sound(config.ambient_sound)
        media.speak("A historia comecou. Mostrem a palma aberta ou a mao fechada.")
        robot.send_command("stage_right", "wake_up", mode="narrative")

    @staticmethod
    def _start_story_from_gesture(
        event: StoryEvent,
        state_manager: StateManager,
        media: MediaController,
        robot: RobotComm,
        config: AppConfig,
    ) -> None:
        state_manager.set_choice("intro_gesture", event.value)
        StoryEngine._start_story(event, state_manager, media, robot, config)

    @staticmethod
    def _enter_crossroads(
        _: StoryEvent,
        __: StateManager,
        media: MediaController,
        robot: RobotComm,
        ___: AppConfig,
    ) -> None:
        media.speak("HAND_OPEN cria um caminho de confianca. HAND_CLOSED cria um caminho de tensao.")
        robot.send_command("stage_both", "await_choice", scene="crossroads")

    @staticmethod
    def _choose_light_path(
        event: StoryEvent,
        state_manager: StateManager,
        media: MediaController,
        robot: RobotComm,
        _: AppConfig,
    ) -> None:
        state_manager.set_choice("path", "light")
        state_manager.add_clue("open_hand_seen")
        state_manager.set_choice("crossroads_gesture", event.value)
        media.speak("Caminho da luz selecionado. O portal final aguarda uma direcao.")
        robot.send_command("stage_left", "soft_pulse", emotion="trust")

    @staticmethod
    def _choose_shadow_path(
        event: StoryEvent,
        state_manager: StateManager,
        media: MediaController,
        robot: RobotComm,
        _: AppConfig,
    ) -> None:
        state_manager.set_choice("path", "shadow")
        state_manager.add_clue("closed_hand_seen")
        state_manager.set_choice("crossroads_gesture", event.value)
        media.speak("Caminho da sombra selecionado. O portal final aguarda uma direcao.")
        robot.send_command("stage_right", "hard_pulse", emotion="tension")

    @staticmethod
    def _enter_ritual_gate(
        _: StoryEvent,
        state_manager: StateManager,
        media: MediaController,
        robot: RobotComm,
        ___: AppConfig,
    ) -> None:
        state_manager.set_flag("ritual_ready", True)
        chosen_path = state_manager.get_choice("path")
        media.speak(
            f"Portal ativo para o caminho '{chosen_path}'. Use POINT_LEFT ou POINT_RIGHT para concluir."
        )
        robot.send_command("stage_both", "await_direction", path=chosen_path or "unknown")

    @staticmethod
    def _play_light_ending(
        event: StoryEvent,
        state_manager: StateManager,
        media: MediaController,
        robot: RobotComm,
        config: AppConfig,
    ) -> None:
        state_manager.set_choice("ending_gesture", event.value)
        state_manager.set_choice("ending", "light")
        media.play_sound(config.success_sound)
        media.speak("Final luminoso ativado. A historia termina em reconciliacao.")
        robot.send_command("stage_both", "final_pose", ending="light")

    @staticmethod
    def _play_shadow_ending(
        event: StoryEvent,
        state_manager: StateManager,
        media: MediaController,
        robot: RobotComm,
        config: AppConfig,
    ) -> None:
        state_manager.set_choice("ending_gesture", event.value)
        state_manager.set_choice("ending", "shadow")
        media.play_sound(config.failure_sound)
        media.speak("Final sombrio ativado. A historia termina em ruptura.")
        robot.send_command("stage_both", "final_pose", ending="shadow")

    @staticmethod
    def _enter_final_light(
        _: StoryEvent,
        __: StateManager,
        media: MediaController,
        robot: RobotComm,
        ___: AppConfig,
    ) -> None:
        media.speak("Fim: caminho da luz.")
        robot.send_command("stage_both", "hold_pose", ending="light")

    @staticmethod
    def _enter_final_shadow(
        _: StoryEvent,
        __: StateManager,
        media: MediaController,
        robot: RobotComm,
        ___: AppConfig,
    ) -> None:
        media.speak("Fim: caminho da sombra.")
        robot.send_command("stage_both", "hold_pose", ending="shadow")
