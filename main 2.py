from __future__ import annotations

import argparse
from pprint import pprint

from config import AppConfig
from media_controller import MediaController
from robot_comm import RobotComm
from state_manager import StateManager
from story_engine import StoryEngine
from vision import CameraVisionSystem, MockVisionSystem, cv2


def print_help(config: AppConfig) -> None:
    print("\nComandos disponiveis:")
    for item in config.manual_help:
        print(f"  - {item}")


def build_engine(config: AppConfig) -> tuple[StateManager, StoryEngine]:
    state_manager = StateManager()
    media_controller = MediaController()
    robot_comm = RobotComm()
    engine = StoryEngine(state_manager, media_controller, robot_comm, config)
    return state_manager, engine


def run_keyboard_mode(config: AppConfig) -> None:
    state_manager, engine = build_engine(config)
    vision_system = MockVisionSystem()

    print(f"\n{config.title}")
    print("Fluxo: visao -> evento -> engine narrativa -> efeitos de cena.\n")
    print("Modo ativo: teclado")
    print_help(config)

    engine.start()

    while not state_manager.is_terminal():
        raw = input("\nEntrada visual/mock > ").strip()
        normalized = raw.lower()

        if normalized == "quit":
            print("Execucao encerrada pelo operador.")
            return

        if normalized == "help":
            print_help(config)
            continue

        if normalized == "status":
            pprint(state_manager.snapshot(), sort_dicts=False)
            continue

        event = vision_system.parse_input(raw)
        if event is None:
            print("Entrada invalida. Use 'help' para ver os comandos.")
            continue

        engine.process_event(event)

    print("\nEstado final:")
    pprint(state_manager.snapshot(), sort_dicts=False)


def run_camera_mode(config: AppConfig) -> None:
    if cv2 is None:
        raise RuntimeError("OpenCV nao esta disponivel no interpretador atual.")

    state_manager, engine = build_engine(config)
    vision_system = CameraVisionSystem(config)

    print(f"\n{config.title}")
    print("Fluxo: camera -> MediaPipe -> evento -> engine narrativa -> efeitos de cena.\n")
    print("Modo ativo: camera")
    print("Mostre a mao para a camera. Gestos suportados: HAND_OPEN, HAND_CLOSED, POINT_LEFT, POINT_RIGHT.")
    print("A cena INTRO pode ser iniciada com HAND_OPEN. Pressione Q na janela da camera para sair.")

    engine.start()

    try:
        while not state_manager.is_terminal():
            frame_result = vision_system.read_event()
            if frame_result.event is not None:
                print(f"[VISION] {frame_result.event.value}")
                engine.process_event(frame_result.event)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                print("Execucao encerrada pelo operador.")
                return

        print("\nEstado final:")
        pprint(state_manager.snapshot(), sort_dicts=False)
        print("Pressione Q na janela da camera para fechar.")
        while True:
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                return
    finally:
        vision_system.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Narrative engine com entrada por teclado ou camera.")
    parser.add_argument(
        "--mode",
        choices=("keyboard", "camera"),
        default="keyboard",
        help="Seleciona a origem dos eventos.",
    )
    parser.add_argument("--camera-index", type=int, default=0, help="Indice da camera para o OpenCV.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = AppConfig(camera_index=args.camera_index)

    if args.mode == "camera":
        run_camera_mode(config)
        return

    run_keyboard_mode(config)


if __name__ == "__main__":
    main()
