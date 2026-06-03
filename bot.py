from __future__ import annotations

import asyncio
import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

from telegram import Update
from telegram.ext import Application, ApplicationBuilder, CommandHandler, ContextTypes

from config import BotConfig, load_config
from modules import docker, services, system, updates
from modules.security import ConfirmationManager


CONFIG: BotConfig = load_config()
CONFIRMATIONS = ConfirmationManager(CONFIG.confirm_ttl_seconds)
LOGGER = logging.getLogger("debian-telegram-admin-bot")
CONFIRM_TOKEN_RE = re.compile(r"^[a-f0-9]{8}$")


def setup_logging(log_file: Path) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=5),
            logging.StreamHandler(),
        ],
    )


def chat_id(update: Update) -> int | None:
    return update.effective_chat.id if update.effective_chat else None


def is_authorized(update: Update) -> bool:
    cid = chat_id(update)
    return CONFIG.authorized_chat_id is not None and cid == CONFIG.authorized_chat_id


async def send_text(update: Update, text: str) -> None:
    if not update.effective_message:
        return
    limit = max(500, CONFIG.max_telegram_message_length)
    clean = text.strip() or "(sin salida)"
    for start in range(0, len(clean), limit):
        await update.effective_message.reply_text(clean[start : start + limit])


async def deny(update: Update) -> None:
    cid = chat_id(update)
    LOGGER.warning("Acceso denegado chat_id=%s", cid)
    await send_text(update, "Acceso denegado.")


def command_args(context: ContextTypes.DEFAULT_TYPE) -> list[str]:
    return [arg.strip() for arg in context.args if arg.strip()]


def help_text() -> str:
    return "\n".join(
        [
            "Bot de administracion Debian",
            "",
            "Comandos:",
            "/start - ayuda basica",
            "/help - lista comandos",
            "/whoami - muestra tu chat_id",
            "/status - estado general",
            "/ram - uso de memoria",
            "/disk - uso de disco",
            "/ip - IP local",
            "/services - servicios permitidos",
            "/service_status nombre",
            "/service_start nombre",
            "/service_stop nombre",
            "/service_restart nombre",
            "/service_logs nombre",
            "/processes - procesos principales",
            "/docker_ps - contenedores Docker",
            "/updates - apt update y lista de actualizaciones",
            "/upgrade_confirm - solicita confirmacion para apt upgrade -y",
            "/reboot_confirm - solicita confirmacion para reiniciar",
            "/confirm TOKEN - ejecuta una accion pendiente",
        ]
    )


async def require_authorized(update: Update) -> bool:
    if is_authorized(update):
        return True
    await deny(update)
    return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if CONFIG.registration_mode and CONFIG.authorized_chat_id is None:
        await send_text(
            update,
            "Modo registro activo. Ejecuta /whoami para ver tu chat_id y luego fija "
            "AUTHORIZED_CHAT_ID en el archivo .env.",
        )
        return
    if not await require_authorized(update):
        return
    await send_text(update, help_text())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if not await require_authorized(update):
        return
    await send_text(update, help_text())


async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    cid = chat_id(update)
    await send_text(update, f"Tu chat_id es: {cid}")


async def run_readonly(
    update: Update,
    description: str,
    func,
) -> None:
    if not await require_authorized(update):
        return
    LOGGER.info("Ejecutando %s chat_id=%s", description, chat_id(update))
    result = await asyncio.to_thread(
        func,
        CONFIG.command_timeout_seconds,
        CONFIG.max_telegram_message_length,
    )
    await send_text(update, result.output)


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    await run_readonly(update, "status", system.status)


async def ram(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    await run_readonly(update, "ram", system.ram)


async def disk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    await run_readonly(update, "disk", system.disk)


async def ip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    await run_readonly(update, "ip", system.local_ip)


async def processes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    await run_readonly(update, "processes", system.processes)


async def docker_ps(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    await run_readonly(update, "docker_ps", docker.docker_ps)


async def list_services(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if not await require_authorized(update):
        return
    await send_text(update, services.list_services(CONFIG.allowed_services))


async def service_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    action: str,
    dangerous: bool = False,
) -> None:
    if not await require_authorized(update):
        return
    args = command_args(context)
    if len(args) != 1:
        await send_text(update, f"Uso: /service_{action} nombre")
        return
    valid, service_or_error = services.validate_service(
        args[0], CONFIG.allowed_services
    )
    if not valid:
        await send_text(update, service_or_error)
        return

    service = service_or_error
    description = f"systemctl {action} {service}"

    def execute() -> system.CommandResult:
        return services.systemctl(
            action,
            service,
            CONFIG.command_timeout_seconds,
            CONFIG.max_telegram_message_length,
        )

    if dangerous:
        pending = CONFIRMATIONS.create(chat_id(update) or 0, description, execute)
        LOGGER.info("Confirmacion creada para %s chat_id=%s", description, chat_id(update))
        await send_text(
            update,
            f"Accion peligrosa: {description}\n"
            f"Confirma en {CONFIG.confirm_ttl_seconds}s con:\n/confirm {pending.token}",
        )
        return

    LOGGER.info("Ejecutando %s chat_id=%s", description, chat_id(update))
    result = await asyncio.to_thread(execute)
    await send_text(update, result.output)


async def service_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await service_command(update, context, "status")


async def service_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await service_command(update, context, "start")


async def service_stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await service_command(update, context, "stop", dangerous=True)


async def service_restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await service_command(update, context, "restart", dangerous=True)


async def service_logs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_authorized(update):
        return
    args = command_args(context)
    if len(args) != 1:
        await send_text(update, "Uso: /service_logs nombre")
        return
    valid, service_or_error = services.validate_service(
        args[0], CONFIG.allowed_services
    )
    if not valid:
        await send_text(update, service_or_error)
        return
    service = service_or_error
    LOGGER.info("Ejecutando journalctl para %s chat_id=%s", service, chat_id(update))
    result = await asyncio.to_thread(
        services.logs,
        service,
        CONFIG.command_timeout_seconds,
        CONFIG.max_telegram_message_length,
    )
    await send_text(update, result.output)


async def list_updates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    await run_readonly(update, "updates", updates.list_updates)


async def upgrade_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if not await require_authorized(update):
        return

    def execute() -> system.CommandResult:
        return updates.upgrade(
            CONFIG.command_timeout_seconds * 20,
            CONFIG.max_telegram_message_length,
        )

    pending = CONFIRMATIONS.create(chat_id(update) or 0, "apt upgrade -y", execute)
    LOGGER.info("Confirmacion creada para apt upgrade chat_id=%s", chat_id(update))
    await send_text(
        update,
        f"Accion peligrosa: apt upgrade -y\n"
        f"Confirma en {CONFIG.confirm_ttl_seconds}s con:\n/confirm {pending.token}",
    )


async def reboot_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if not await require_authorized(update):
        return

    def execute() -> system.CommandResult:
        return system.run_command(
            ["sudo", "/usr/sbin/reboot"],
            timeout=CONFIG.command_timeout_seconds,
            max_chars=CONFIG.max_telegram_message_length,
        )

    pending = CONFIRMATIONS.create(chat_id(update) or 0, "reboot", execute)
    LOGGER.info("Confirmacion creada para reboot chat_id=%s", chat_id(update))
    await send_text(
        update,
        f"Accion peligrosa: reiniciar el servidor\n"
        f"Confirma en {CONFIG.confirm_ttl_seconds}s con:\n/confirm {pending.token}",
    )


async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_authorized(update):
        return
    args = command_args(context)
    if len(args) != 1 or not CONFIRM_TOKEN_RE.fullmatch(args[0]):
        await send_text(update, "Uso: /confirm TOKEN")
        return

    ok, description, action = CONFIRMATIONS.consume(args[0], chat_id(update) or 0)
    if not ok or action is None:
        await send_text(update, description)
        return

    LOGGER.warning("Ejecutando accion confirmada: %s chat_id=%s", description, chat_id(update))
    await send_text(update, f"Ejecutando: {description}")
    result = await asyncio.to_thread(action)
    await send_text(update, result.output)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    LOGGER.exception("Error no controlado", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        await send_text(update, "Ocurrio un error interno. Revisa los logs del bot.")


def build_application() -> Application:
    app = ApplicationBuilder().token(CONFIG.telegram_bot_token).build()
    handlers = {
        "start": start,
        "help": help_command,
        "whoami": whoami,
        "status": status,
        "ram": ram,
        "disk": disk,
        "ip": ip,
        "services": list_services,
        "service_status": service_status,
        "service_start": service_start,
        "service_stop": service_stop,
        "service_restart": service_restart,
        "service_logs": service_logs,
        "processes": processes,
        "docker_ps": docker_ps,
        "updates": list_updates,
        "upgrade_confirm": upgrade_confirm,
        "reboot_confirm": reboot_confirm,
        "confirm": confirm,
    }
    for name, handler in handlers.items():
        app.add_handler(CommandHandler(name, handler))
    app.add_error_handler(error_handler)
    return app


def main() -> None:
    setup_logging(CONFIG.log_file)
    LOGGER.info("Iniciando bot servicio=%s", CONFIG.service_name)
    build_application().run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
