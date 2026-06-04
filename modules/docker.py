from __future__ import annotations

import re
from pathlib import Path

from modules.system import CommandResult, run_command

CONTAINER_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


def validate_container_name(name: str) -> tuple[bool, str]:
    container = name.strip()
    if not container:
        return False, "Debes seleccionar un contenedor."
    if not CONTAINER_NAME_RE.fullmatch(container):
        return False, "Nombre de contenedor invalido."
    return True, container


def _docker_available() -> bool:
    return Path("/usr/bin/docker").exists()


def list_container_names(timeout: int, max_chars: int) -> list[str]:
    if not _docker_available():
        return []
    result = run_command(
        [
            "sudo",
            "/usr/bin/docker",
            "ps",
            "-a",
            "--format",
            "{{.Names}}",
        ],
        timeout=timeout,
        max_chars=max_chars,
    )
    if not result.ok:
        return []
    containers = []
    for line in result.output.splitlines():
        name = line.strip()
        valid, container = validate_container_name(name)
        if valid and container not in containers:
            containers.append(container)
    return containers


def docker_ps(timeout: int, max_chars: int) -> CommandResult:
    if not _docker_available():
        return CommandResult(False, "Docker no esta instalado en /usr/bin/docker.")
    names = list_container_names(timeout, max_chars)
    if not names:
        return CommandResult(True, "No hay contenedores Docker o no se pudieron listar.")
    return CommandResult(True, "Contenedores Docker:\n" + "\n".join(f"- {name}" for name in names))


def container_action(
    action: str,
    container_name: str,
    timeout: int,
    max_chars: int,
) -> CommandResult:
    if action not in {"start", "stop", "restart"}:
        return CommandResult(False, "Accion Docker no permitida.")
    if not _docker_available():
        return CommandResult(False, "Docker no esta instalado en /usr/bin/docker.")
    valid, container = validate_container_name(container_name)
    if not valid:
        return CommandResult(False, container)
    return run_command(
        [
            "sudo",
            "/usr/bin/docker",
            action,
            container,
        ],
        timeout=timeout,
        max_chars=max_chars,
    )


def container_logs(container_name: str, timeout: int, max_chars: int) -> CommandResult:
    if not _docker_available():
        return CommandResult(False, "Docker no esta instalado en /usr/bin/docker.")
    valid, container = validate_container_name(container_name)
    if not valid:
        return CommandResult(False, container)
    return run_command(
        ["sudo", "/usr/bin/docker", "logs", "--tail", "100", container],
        timeout=timeout,
        max_chars=max_chars,
    )


def docker_stats(timeout: int, max_chars: int) -> CommandResult:
    if not _docker_available():
        return CommandResult(False, "Docker no esta instalado en /usr/bin/docker.")
    return run_command(
        [
            "sudo",
            "/usr/bin/docker",
            "stats",
            "--no-stream",
            "--format",
            "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}",
        ],
        timeout=timeout,
        max_chars=max_chars,
    )
