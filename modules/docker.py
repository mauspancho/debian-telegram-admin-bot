from __future__ import annotations

from modules.system import CommandResult, command_exists, run_command


def docker_ps(timeout: int, max_chars: int) -> CommandResult:
    if not command_exists("docker"):
        return CommandResult(False, "Docker no esta instalado o no esta en PATH.")
    return run_command(
        [
            "docker",
            "ps",
            "--format",
            "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}",
        ],
        timeout=timeout,
        max_chars=max_chars,
    )
