from __future__ import annotations

import re

from modules.system import CommandResult, run_command

SERVICE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.@-]*$")


def normalize_service_name(name: str) -> str:
    return name.strip()


def validate_service(name: str, allowed_services: list[str]) -> tuple[bool, str]:
    service = normalize_service_name(name)
    if not service:
        return False, "Debes indicar el nombre del servicio."
    if not SERVICE_NAME_RE.fullmatch(service):
        return False, "Nombre de servicio invalido."
    if service not in allowed_services:
        return False, f"Servicio no permitido: {service}"
    return True, service


def list_services(allowed_services: list[str]) -> str:
    if not allowed_services:
        return "No hay servicios permitidos configurados."
    return "Servicios permitidos:\n" + "\n".join(f"- {name}" for name in allowed_services)


def systemctl(
    action: str,
    service: str,
    timeout: int,
    max_chars: int,
) -> CommandResult:
    args = ["sudo", "/usr/bin/systemctl", action, service]
    if action == "status":
        args.append("--no-pager")
    return run_command(args, timeout=timeout, max_chars=max_chars)


def logs(service: str, timeout: int, max_chars: int) -> CommandResult:
    return run_command(
        ["sudo", "/usr/bin/journalctl", "-u", service, "-n", "80", "--no-pager"],
        timeout=timeout,
        max_chars=max_chars,
    )
