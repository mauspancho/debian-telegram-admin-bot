from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


SERVICE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.@-]*$")


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


@dataclass(frozen=True)
class BotConfig:
    telegram_bot_token: str
    authorized_chat_id: int | None
    registration_mode: bool
    allow_all_systemd_services: bool
    allowed_services: list[str]
    service_name: str
    install_path: Path
    log_file: Path
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

    chat_id_raw = os.getenv("AUTHORIZED_CHAT_ID", "").strip()
    registration_mode = _bool_from_env(os.getenv("REGISTRATION_MODE"), False)
    authorized_chat_id: int | None = None
    if chat_id_raw:
        try:
            authorized_chat_id = int(chat_id_raw)
        except ValueError as exc:
            raise ValueError("AUTHORIZED_CHAT_ID debe ser numerico") from exc
    elif not registration_mode:
        raise ValueError(
            "AUTHORIZED_CHAT_ID es obligatorio salvo que REGISTRATION_MODE=true"
        )

    install_path = Path(os.getenv("INSTALL_PATH", str(base_dir))).expanduser()
    log_file = Path(
        os.getenv("LOG_FILE", str(install_path / "logs" / "bot.log"))
    ).expanduser()

    return BotConfig(
        telegram_bot_token=token,
        authorized_chat_id=authorized_chat_id,
        registration_mode=registration_mode,
        allow_all_systemd_services=_bool_from_env(
            os.getenv("ALLOW_ALL_SYSTEMD_SERVICES"), False
        ),
        allowed_services=_services_from_env(os.getenv("ALLOWED_SERVICES")),
        service_name=os.getenv("SERVICE_NAME", "debian-telegram-admin-bot").strip()
        or "debian-telegram-admin-bot",
        install_path=install_path,
        log_file=log_file,
        confirm_ttl_seconds=_int_from_env("CONFIRM_TTL_SECONDS", 180),
        command_timeout_seconds=_int_from_env("COMMAND_TIMEOUT_SECONDS", 30),
        max_telegram_message_length=_int_from_env(
            "MAX_TELEGRAM_MESSAGE_LENGTH", 3500
        ),
    )
