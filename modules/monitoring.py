from __future__ import annotations

import getpass
import os
import stat
from pathlib import Path

from modules import system
from modules.system import CommandResult, limit_text, run_command


def report(timeout: int, max_chars: int) -> CommandResult:
    parts = [
        ("Estado", system.status(timeout, max_chars).output),
        ("Memoria", system.ram(timeout, max_chars).output),
        ("Disco", system.disk(timeout, max_chars).output),
        ("IP", system.local_ip(timeout, max_chars).output),
    ]
    output = "\n\n".join(f"## {title}\n{body}" for title, body in parts)
    return CommandResult(True, limit_text(output, max_chars))


def disk_alerts(timeout: int, max_chars: int, threshold: int = 80) -> CommandResult:
    result = run_command(
        ["/usr/bin/df", "-P", "-h", "-x", "tmpfs", "-x", "devtmpfs"],
        timeout=timeout,
        max_chars=max_chars,
    )
    if not result.ok:
        return result

    alerts: list[str] = []
    for line in result.output.splitlines()[1:]:
        parts = line.split()
        if len(parts) < 6 or not parts[4].endswith("%"):
            continue
        try:
            used = int(parts[4].rstrip("%"))
        except ValueError:
            continue
        if used >= threshold:
            alerts.append(f"{parts[5]}: {parts[4]} usado ({parts[2]}/{parts[1]})")

    if not alerts:
        return CommandResult(True, f"No hay discos sobre {threshold}% de uso.")
    return CommandResult(True, "Alertas de disco:\n" + "\n".join(alerts))


def _mode(path: Path) -> str:
    try:
        return oct(stat.S_IMODE(path.stat().st_mode))
    except OSError:
        return "no disponible"


def security_check(
    install_path: Path,
    log_file: Path,
    service_name: str,
    timeout: int,
    max_chars: int,
) -> CommandResult:
    checks: list[str] = []
    current_user = getpass.getuser()
    checks.append(f"Usuario actual: {current_user}")
    checks.append(f"EUID: {getattr(os, 'geteuid', lambda: 'no disponible')()}")

    env_file = install_path / ".env"
    checks.append(f".env existe: {'si' if env_file.exists() else 'no'}")
    checks.append(f".env permisos: {_mode(env_file)}")
    if env_file.exists():
        mode = stat.S_IMODE(env_file.stat().st_mode)
        checks.append(f".env no publico: {'si' if mode & 0o007 == 0 else 'no'}")

    sudoers = Path("/etc/sudoers.d/debian-telegram-admin-bot")
    checks.append(f"sudoers existe: {'si' if sudoers.exists() else 'no'}")
    checks.append(f"sudoers permisos: {_mode(sudoers)}")

    log_dir = log_file.parent
    checks.append(f"directorio logs existe: {'si' if log_dir.exists() else 'no'}")
    checks.append(f"servicio configurado: {service_name}")

    sudo_check = run_command(["/usr/sbin/visudo", "-c"], timeout=timeout, max_chars=1000)
    checks.append(f"visudo -c: {'ok' if sudo_check.ok else 'fallo'}")

    return CommandResult(True, limit_text("\n".join(checks), max_chars))
