from __future__ import annotations

import tarfile
import time
from pathlib import Path

from modules.system import CommandResult, limit_text


def list_backups(
    backup_targets: dict[str, Path],
    backup_path: Path,
    max_chars: int,
) -> CommandResult:
    lines: list[str] = ["Targets configurados:"]
    if not backup_targets:
        lines.append("- ninguno")
    for name, target in backup_targets.items():
        lines.append(f"- {name}: {target}")

    lines.append("")
    lines.append("Backups disponibles:")
    if not backup_path.exists():
        lines.append("- ninguno")
    else:
        files = sorted(backup_path.glob("*.tar.gz"))
        if not files:
            lines.append("- ninguno")
        for item in files[-50:]:
            lines.append(f"- {item.name}")

    return CommandResult(True, limit_text("\n".join(lines), max_chars))


def _target(name: str, backup_targets: dict[str, Path]) -> tuple[bool, str, Path | None]:
    clean = name.strip()
    if clean not in backup_targets:
        return False, f"Backup target no permitido: {clean}", None
    return True, clean, backup_targets[clean]


def create_backup(
    name: str,
    backup_targets: dict[str, Path],
    backup_path: Path,
    max_chars: int,
) -> CommandResult:
    ok, clean, target = _target(name, backup_targets)
    if not ok or target is None:
        return CommandResult(False, clean)
    if not target.exists():
        return CommandResult(False, f"Ruta target no existe: {target}")

    backup_path.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    archive = backup_path / f"{clean}-{timestamp}.tar.gz"

    with tarfile.open(archive, "w:gz") as tar:
        tar.add(target, arcname=target.name)

    return CommandResult(True, limit_text(f"Backup creado:\n{archive}", max_chars))


def _safe_extract(tar: tarfile.TarFile, destination: Path) -> None:
    base = destination.resolve()
    for member in tar.getmembers():
        if member.issym() or member.islnk():
            raise ValueError(f"Enlace no permitido en tar: {member.name}")
        target = (destination / member.name).resolve()
        if base != target and base not in target.parents:
            raise ValueError(f"Entrada insegura en tar: {member.name}")
    tar.extractall(destination)


def restore_backup(
    name: str,
    backup_targets: dict[str, Path],
    backup_path: Path,
    max_chars: int,
) -> CommandResult:
    ok, clean, target = _target(name, backup_targets)
    if not ok or target is None:
        return CommandResult(False, clean)

    files = sorted(backup_path.glob(f"{clean}-*.tar.gz"))
    if not files:
        return CommandResult(False, f"No hay backups para {clean}")
    archive = files[-1]
    parent = target.parent
    parent.mkdir(parents=True, exist_ok=True)

    with tarfile.open(archive, "r:gz") as tar:
        _safe_extract(tar, parent)

    return CommandResult(True, limit_text(f"Backup restaurado:\n{archive}", max_chars))
