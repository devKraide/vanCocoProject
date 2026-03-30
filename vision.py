from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from time import monotonic
from typing import Any

from config import AppConfig, EventType, GestureType, StoryEvent

try:
    import cv2  # type: ignore
    import mediapipe as mp  # type: ignore
except ImportError:  # pragma: no cover - depende do ambiente local
    cv2 = None
    mp = None


class MockVisionSystem:
    """Simula a camada de visao convertendo entradas em eventos."""

    def parse_input(self, raw_value: str) -> StoryEvent | None:
        token = raw_value.strip()
        if not token:
            return None

        lowered = token.lower()
        if lowered == "start":
            return StoryEvent(EventType.START, "BEGIN_STORY", "keyboard")

        if lowered.startswith("gesture:"):
            gesture_name = token.split(":", 1)[1].strip().upper()
            if gesture_name not in GestureType._value2member_map_:
                return None
            return StoryEvent(EventType.GESTURE, gesture_name, "vision_mock")

        return None


@dataclass(frozen=True)
class VisionFrameResult:
    event: StoryEvent | None
    debug_text: str


class MediaPipeGestureAdapter:
    """Classifica landmarks da mao em gestos de alto nivel."""

    THUMB_TIP = 4
    THUMB_IP = 3
    INDEX_MCP = 5
    INDEX_PIP = 6
    INDEX_TIP = 8
    MIDDLE_PIP = 10
    MIDDLE_TIP = 12
    RING_PIP = 14
    RING_TIP = 16
    PINKY_PIP = 18
    PINKY_TIP = 20

    def classify_landmarks(self, hand_landmarks: Any, handedness_label: str) -> GestureType | None:
        points = hand_landmarks.landmark
        label = handedness_label.lower()

        fingers_up = {
            "thumb": self._thumb_is_open(points, label),
            "index": points[self.INDEX_TIP].y < points[self.INDEX_PIP].y,
            "middle": points[self.MIDDLE_TIP].y < points[self.MIDDLE_PIP].y,
            "ring": points[self.RING_TIP].y < points[self.RING_PIP].y,
            "pinky": points[self.PINKY_TIP].y < points[self.PINKY_PIP].y,
        }

        if all(fingers_up.values()):
            return GestureType.HAND_OPEN

        if not any(fingers_up.values()):
            return GestureType.HAND_CLOSED

        only_index_up = (
            fingers_up["index"]
            and not fingers_up["middle"]
            and not fingers_up["ring"]
            and not fingers_up["pinky"]
        )
        if only_index_up:
            wrist_x = points[0].x
            index_x = points[self.INDEX_TIP].x
            horizontal_delta = index_x - wrist_x
            if horizontal_delta < -0.12:
                return GestureType.POINT_LEFT
            if horizontal_delta > 0.12:
                return GestureType.POINT_RIGHT

        return None

    def _thumb_is_open(self, points: Any, handedness_label: str) -> bool:
        thumb_tip_x = points[self.THUMB_TIP].x
        thumb_ip_x = points[self.THUMB_IP].x
        if handedness_label == "right":
            return thumb_tip_x < thumb_ip_x
        return thumb_tip_x > thumb_ip_x


class CameraVisionSystem:
    """Captura a camera, classifica gestos e emite eventos estaveis."""

    def __init__(self, config: AppConfig) -> None:
        if cv2 is None or mp is None:
            raise RuntimeError(
                "OpenCV/MediaPipe nao estao instalados para o interpretador atual."
            )

        self.config = config
        self.adapter = MediaPipeGestureAdapter()
        self.cap = cv2.VideoCapture(config.camera_index)
        if not self.cap.isOpened():
            raise RuntimeError(f"Nao foi possivel abrir a camera no indice {config.camera_index}.")

        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=config.min_detection_confidence,
            min_tracking_confidence=config.min_tracking_confidence,
        )
        self.gesture_window: deque[GestureType] = deque(maxlen=config.stable_frames_required)
        self.last_emitted_gesture: GestureType | None = None
        self.last_emit_time = 0.0

    def read_event(self) -> VisionFrameResult:
        ok, frame = self.cap.read()
        if not ok:
            return VisionFrameResult(None, "camera_read_failed")

        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)

        detected_gesture: GestureType | None = None
        debug_text = "NO_HAND"

        if results.multi_hand_landmarks and results.multi_handedness:
            hand_landmarks = results.multi_hand_landmarks[0]
            handedness_label = results.multi_handedness[0].classification[0].label
            self.mp_drawing.draw_landmarks(
                frame,
                hand_landmarks,
                self.mp_hands.HAND_CONNECTIONS,
            )
            detected_gesture = self.adapter.classify_landmarks(hand_landmarks, handedness_label)
            debug_text = detected_gesture.value if detected_gesture else "UNKNOWN_GESTURE"

        event = self._build_stable_event(detected_gesture)
        self._draw_overlay(frame, debug_text, event)
        cv2.imshow("CocoWizard Gesture Input", frame)
        return VisionFrameResult(event, debug_text)

    def close(self) -> None:
        self.cap.release()
        self.hands.close()
        cv2.destroyAllWindows()

    def _build_stable_event(self, gesture: GestureType | None) -> StoryEvent | None:
        if gesture is None:
            self.gesture_window.clear()
            return None

        self.gesture_window.append(gesture)
        if len(self.gesture_window) < self.config.stable_frames_required:
            return None

        stable_gesture = self.gesture_window[0]
        if any(item != stable_gesture for item in self.gesture_window):
            return None

        now = monotonic()
        if (
            self.last_emitted_gesture == stable_gesture
            and now - self.last_emit_time < self.config.event_cooldown_seconds
        ):
            return None

        self.last_emitted_gesture = stable_gesture
        self.last_emit_time = now
        return StoryEvent(EventType.GESTURE, stable_gesture.value, "camera")

    def _draw_overlay(self, frame: Any, debug_text: str, event: StoryEvent | None) -> None:
        event_text = event.value if event else "-"
        cv2.putText(
            frame,
            f"Gesture: {debug_text}",
            (20, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )
        cv2.putText(
            frame,
            f"Event: {event_text}",
            (20, 65),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        cv2.putText(
            frame,
            "Pressione Q para sair",
            (20, 100),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 0),
            2,
            cv2.LINE_AA,
        )
