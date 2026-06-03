from __future__ import annotations

import re

from modules.system import CommandResult, run_command

SERVICE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.@-]*$")


def normalize_service_name(name: str) -> str:
    return name.strip()


def normalize_systemd_service_name(name: str) -> str:
    service = normalize_service_name(name)
    if "." not in service:
        return f"{service}.service"
    return service


def _parse_unit_names(output: str) -> list[str]:
    units: list[str] = []
    for line in output.splitlines():
        parts = line.split()
        if not parts:
            continue
        unit = parts[0].strip()
        if unit.endswith(".service") and SERVICE_NAME_RE.fullmatch(unit):
            units.append(unit)
    return units


def installed_services(timeout: int = 10, max_chars: int = 20000) -> list[str]:
    result = run_command(
        [
            "/usr/bin/systemctl",
            "list-unit-files",
            "--type=service",
            "--no-legend",
            "--no-pager",
        ],
        timeout=timeout,
        max_chars=max_chars,
    )
    if not result.ok:
        return []
    return _parse_unit_names(result.output)


def service_exists(service: str, timeout: int = 10) -> bool:
    unit = normalize_systemd_service_name(service)
    result = run_command(
        [
            "/usr/bin/systemctl",
            "list-unit-files",
            unit,
            "--type=service",
            "--no-legend",
            "--no-pager",
        ],
        timeout=timeout,
        max_chars=2000,
    )
    return result.ok and unit in _parse_unit_names(result.output)


def validate_service(
    name: str,
    allowed_services: list[str],
    allow_all_systemd_services: bool = False,
    timeout: int = 10,
) -> tuple[bool, str]:
    service = normalize_service_name(name)
    if not service:
        return False, "Debes indicar el nombre del servicio."
    if not SERVICE_NAME_RE.fullmatch(service):
        return False, "Nombre de servicio invalido."
    if allow_all_systemd_services:
        service = normalize_systemd_service_name(service)
        if not service_exists(service, timeout=timeout):
            return False, f"Servicio systemd no encontrado: {service}"
        return True, service
    if service not in allowed_services:
        return False, f"Servicio no permitido: {service}"
    return True, service


def list_services(
    allowed_services: list[str],
    allow_all_systemd_services: bool = False,
    timeout: int = 10,
) -> str:
    if allow_all_systemd_services:
        units = installed_services(timeout=timeout)
        if not units:
            return "Modo todos los servicios activo, pero no se pudieron listar unidades systemd."
        preview = "\n".join(f"- {name}" for name in units[:120])
        extra = ""
        if len(units) > 120:
            extra = f"\n... y {len(units) - 120} servicios mas."
        return (
            f"Modo todos los servicios systemd activo ({len(units)} servicios).\n"
            f"{preview}{extra}"
        )
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
