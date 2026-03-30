from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum
from time import sleep
from typing import Callable

from media_controller import MediaController
from robot_comm import RobotComm


class CueType(str, Enum):
    VIDEO = "video"
    WAIT = "wait"
    WAIT_MANUAL = "wait_manual"
    ROBOT = "robot"


@dataclass(frozen=True)
class Cue:
    cue_type: CueType
    payload: dict[str, object]

    @classmethod
    def from_dict(cls, raw_cue: dict[str, object]) -> "Cue":
        cue_type = raw_cue.get("type")
        if cue_type not in CueType._value2member_map_:
            raise ValueError(f"Tipo de cue invalido: {cue_type}")

        payload = {key: value for key, value in raw_cue.items() if key != "type"}
        return cls(CueType(cue_type), payload)


class CueEngine:
    """Executa cues em ordem FIFO."""

    def __init__(
        self,
        cues: list[dict[str, object]],
        media_controller: MediaController,
        robot_comm: RobotComm,
        input_func: Callable[[str], str] = input,
    ) -> None:
        self.queue: deque[Cue] = deque(Cue.from_dict(cue) for cue in cues)
        self.media_controller = media_controller
        self.robot_comm = robot_comm
        self.input_func = input_func

    def has_next(self) -> bool:
        return bool(self.queue)

    def run(self) -> None:
        while self.has_next():
            self.run_next()

    def run_next(self) -> None:
        cue = self.queue.popleft()
        print(f"\n[CUE] {cue.cue_type.value} {cue.payload}")
        handler = self._handlers()[cue.cue_type]
        handler(cue)

    def _handlers(self) -> dict[CueType, Callable[[Cue], None]]:
        return {
            CueType.VIDEO: self._handle_video,
            CueType.WAIT: self._handle_wait,
            CueType.WAIT_MANUAL: self._handle_wait_manual,
            CueType.ROBOT: self._handle_robot,
        }

    def _handle_video(self, cue: Cue) -> None:
        file_path = str(cue.payload["file"])
        self.media_controller.play_video(file_path)

    def _handle_wait(self, cue: Cue) -> None:
        duration = float(cue.payload["duration"])
        print(f"[CUE] Aguardando {duration:.2f}s")
        sleep(duration)

    def _handle_wait_manual(self, cue: Cue) -> None:
        _ = cue
        while True:
            response = self.input_func("[CUE] Aguardando operador. ENTER/n para continuar, q para abortar: ")
            command = response.strip().lower()
            if command in {"", "n"}:
                return
            if command == "q":
                raise KeyboardInterrupt("Execucao interrompida pelo operador.")
            print("[CUE] Comando invalido. Use ENTER, n ou q.")

    def _handle_robot(self, cue: Cue) -> None:
        command = str(cue.payload["command"])
        self.robot_comm.send_command(command)
