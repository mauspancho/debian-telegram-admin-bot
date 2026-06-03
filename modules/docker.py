from __future__ import annotations

from pathlib import Path

from modules.system import CommandResult, run_command


def docker_ps(timeout: int, max_chars: int) -> CommandResult:
    if not Path("/usr/bin/docker").exists():
        return CommandResult(False, "Docker no esta instalado en /usr/bin/docker.")
    return run_command(
        [
            "sudo",
            "/usr/bin/docker",
            "ps",
            "--format",
            "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}",
        ],
        timeout=timeout,
        max_chars=max_chars,
    )
