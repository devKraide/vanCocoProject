from __future__ import annotations


class RobotComm:
    """Mock simples da camada de comunicacao com robos."""

    def send_command(self, command: str) -> None:
        print(f"[ROBOT] command={command}")
