from __future__ import annotations

from pathlib import Path

try:
    import cv2  # type: ignore
except ImportError:  # pragma: no cover - depende do ambiente local
    cv2 = None


class MediaController:
    """Controla a reproducao de midia do roteiro."""

    def __init__(self, window_name: str = "CocoWizard Playback") -> None:
        self.window_name = window_name

    def play_video(self, path: str) -> None:
        video_path = Path(path)
        if not video_path.exists():
            raise FileNotFoundError(f"Arquivo de video nao encontrado: {video_path}")

        if cv2 is None:
            raise RuntimeError("OpenCV nao esta disponivel para reproducao de video.")

        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            raise RuntimeError(f"Nao foi possivel abrir o video: {video_path}")

        fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
        frame_delay_ms = max(1, int(1000 / fps))

        print(f"[MEDIA] Reproduzindo video: {video_path}")

        try:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break

                cv2.imshow(self.window_name, frame)
                key = cv2.waitKey(frame_delay_ms) & 0xFF
                if key == ord("q"):
                    raise KeyboardInterrupt("Reproducao interrompida pelo operador.")
        finally:
            capture.release()
            cv2.destroyWindow(self.window_name)
