from __future__ import annotations

from cue_engine import CueEngine
from media_controller import MediaController
from robot_comm import RobotComm


def build_show_script() -> list[dict[str, object]]:
    return [
        {"type": "video", "file": "midia/video1.mp4"},
        {"type": "wait", "duration": 2},
        {"type": "wait_manual"},
        {"type": "video", "file": "midia/video2.mp4"},
        {"type": "robot", "command": "MOVE_FORWARD"},
    ]


def main() -> None:
    cues = build_show_script()
    media_controller = MediaController()
    robot_comm = RobotComm()
    engine = CueEngine(cues, media_controller, robot_comm)

    print("CocoWizard Cue Engine")
    print("Execucao FIFO de cues para teatro/robotica.")
    print("Durante wait_manual: ENTER ou n avancam; q aborta.")
    print("Durante video: q interrompe a execucao.\n")

    try:
        engine.run()
    except KeyboardInterrupt as exc:
        print(f"\n[STOP] {exc}")
        return

    print("\n[FIM] Roteiro concluido com sucesso.")


if __name__ == "__main__":
    main()
