from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


SERVICE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.@-]*$")
BACKUP_TARGET_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")


def _bool_from_env(value: str | None, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on", "si"}


def _int_from_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} debe ser un numero entero") from exc


def _services_from_env(raw: str | None) -> list[str]:
    if not raw:
        return []
    services: list[str] = []
    for item in raw.split(","):
        value = item.strip()
        if value and not SERVICE_NAME_RE.fullmatch(value):
            raise ValueError(f"Servicio invalido en ALLOWED_SERVICES: {value}")
        if value and value not in services:
            services.append(value)
    return services


def _ids_from_env(raw: str | None) -> list[int]:
    if not raw:
        return []
    ids: list[int] = []
    for item in raw.split(","):
        value = item.strip()
        if not value:
            continue
        try:
            chat_id = int(value)
        except ValueError as exc:
            raise ValueError(f"Chat ID invalido: {value}") from exc
        if chat_id not in ids:
            ids.append(chat_id)
    return ids


def _backup_targets_from_env(raw: str | None) -> dict[str, Path]:
    targets: dict[str, Path] = {}
    if not raw:
        return targets
    for item in raw.split(","):
        value = item.strip()
        if not value:
            continue
        if ":" not in value:
            raise ValueError("BACKUP_TARGETS debe usar formato nombre:/ruta")
        name, path_raw = value.split(":", 1)
        name = name.strip()
        path_raw = path_raw.strip()
        if not BACKUP_TARGET_RE.fullmatch(name):
            raise ValueError(f"Nombre de backup invalido: {name}")
        path = Path(path_raw).expanduser()
        if not path.is_absolute():
            raise ValueError(f"Ruta de backup no absoluta para {name}: {path_raw}")
        targets[name] = path
    return targets


@dataclass(frozen=True)
class BotConfig:
    telegram_bot_token: str
    authorized_chat_id: int | None
    authorized_chat_ids: list[int]
    admin_chat_ids: list[int]
    readonly_chat_ids: list[int]
    registration_mode: bool
    allow_all_systemd_services: bool
    allowed_services: list[str]
    service_name: str
    install_path: Path
    log_file: Path
    audit_log_file: Path
    backup_targets: dict[str, Path]
    backup_path: Path
    bot_repo_path: Path | None
    confirm_ttl_seconds: int
    command_timeout_seconds: int
    max_telegram_message_length: int


def load_config() -> BotConfig:
    base_dir = Path(__file__).resolve().parent
    env_path = Path(os.getenv("DEBIAN_BOT_ENV", base_dir / ".env"))
    load_dotenv(env_path)

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN no esta configurado")

    legacy_chat_id_raw = os.getenv("AUTHORIZED_CHAT_ID", "").strip()
    authorized_chat_ids = _ids_from_env(os.getenv("AUTHORIZED_CHAT_IDS"))
    admin_chat_ids = _ids_from_env(os.getenv("ADMIN_CHAT_IDS"))
    readonly_chat_ids = _ids_from_env(os.getenv("READONLY_CHAT_IDS"))
    registration_mode = _bool_from_env(os.getenv("REGISTRATION_MODE"), False)
    legacy_chat_id: int | None = None
    if legacy_chat_id_raw:
        try:
            legacy_chat_id = int(legacy_chat_id_raw)
        except ValueError as exc:
            raise ValueError("AUTHORIZED_CHAT_ID debe ser numerico") from exc
        if legacy_chat_id not in authorized_chat_ids:
            authorized_chat_ids.append(legacy_chat_id)

    for chat_id in admin_chat_ids + readonly_chat_ids:
        if chat_id not in authorized_chat_ids:
            authorized_chat_ids.append(chat_id)

    if not admin_chat_ids:
        admin_chat_ids = [
            chat_id for chat_id in authorized_chat_ids if chat_id not in readonly_chat_ids
        ]

    authorized_chat_id = admin_chat_ids[0] if admin_chat_ids else legacy_chat_id
    if not authorized_chat_ids and not registration_mode:
        raise ValueError(
            "AUTHORIZED_CHAT_IDS o ADMIN_CHAT_IDS es obligatorio salvo que REGISTRATION_MODE=true"
        )

    install_path = Path(os.getenv("INSTALL_PATH", str(base_dir))).expanduser()
    log_file = Path(
        os.getenv("LOG_FILE", str(install_path / "logs" / "bot.log"))
    ).expanduser()
    audit_log_file = Path(
        os.getenv("AUDIT_LOG_FILE", str(install_path / "logs" / "audit.log"))
    ).expanduser()
    backup_path = Path(
        os.getenv("BACKUP_PATH", str(install_path / "backups"))
    ).expanduser()
    bot_repo_raw = os.getenv("BOT_REPO_PATH", "").strip()

    return BotConfig(
        telegram_bot_token=token,
        authorized_chat_id=authorized_chat_id,
        authorized_chat_ids=authorized_chat_ids,
        admin_chat_ids=admin_chat_ids,
        readonly_chat_ids=readonly_chat_ids,
        registration_mode=registration_mode,
        allow_all_systemd_services=_bool_from_env(
            os.getenv("ALLOW_ALL_SYSTEMD_SERVICES"), False
        ),
        allowed_services=_services_from_env(os.getenv("ALLOWED_SERVICES")),
        service_name=os.getenv("SERVICE_NAME", "debian-telegram-admin-bot").strip()
        or "debian-telegram-admin-bot",
        install_path=install_path,
        log_file=log_file,
        audit_log_file=audit_log_file,
        backup_targets=_backup_targets_from_env(os.getenv("BACKUP_TARGETS")),
        backup_path=backup_path,
        bot_repo_path=Path(bot_repo_raw).expanduser() if bot_repo_raw else None,
        confirm_ttl_seconds=_int_from_env("CONFIRM_TTL_SECONDS", 180),
        command_timeout_seconds=_int_from_env("COMMAND_TIMEOUT_SECONDS", 30),
        max_telegram_message_length=_int_from_env(
            "MAX_TELEGRAM_MESSAGE_LENGTH", 3500
        ),
    )
