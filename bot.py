from __future__ import annotations

import asyncio
import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from config import BotConfig, load_config
from modules import docker, services, system, updates
from modules.security import ConfirmationManager


CONFIG: BotConfig = load_config()
CONFIRMATIONS = ConfirmationManager(CONFIG.confirm_ttl_seconds)
LOGGER = logging.getLogger("debian-telegram-admin-bot")
CONFIRM_TOKEN_RE = re.compile(r"^[a-f0-9]{8}$")
SERVICES_PER_PAGE = 8
CONTAINERS_PER_PAGE = 8


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


async def send_text(
    update: Update,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    if not update.effective_message:
        return
    limit = max(500, CONFIG.max_telegram_message_length)
    clean = text.strip() or "(sin salida)"
    for start in range(0, len(clean), limit):
        markup = reply_markup if start == 0 else None
        await update.effective_message.reply_text(
            clean[start : start + limit],
            reply_markup=markup,
        )


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


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Sistema", callback_data="menu:system"),
                InlineKeyboardButton("Servicios", callback_data="svcpage:0"),
            ],
            [
                InlineKeyboardButton("Docker", callback_data="dockerpage:0"),
                InlineKeyboardButton("Actualizaciones", callback_data="menu:updates"),
            ],
            [
                InlineKeyboardButton("Ayuda", callback_data="menu:help"),
                InlineKeyboardButton("Whoami", callback_data="act:whoami"),
            ],
        ]
    )


def system_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Status", callback_data="act:status"),
                InlineKeyboardButton("RAM", callback_data="act:ram"),
            ],
            [
                InlineKeyboardButton("Disco", callback_data="act:disk"),
                InlineKeyboardButton("IP", callback_data="act:ip"),
            ],
            [
                InlineKeyboardButton("Procesos", callback_data="act:processes"),
                InlineKeyboardButton("Volver", callback_data="menu:main"),
            ],
        ]
    )


def updates_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Buscar updates", callback_data="act:updates")],
            [
                InlineKeyboardButton("Upgrade", callback_data="danger:upgrade"),
                InlineKeyboardButton("Reboot", callback_data="danger:reboot"),
            ],
            [InlineKeyboardButton("Volver", callback_data="menu:main")],
        ]
    )


def service_action_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Status", callback_data="svcaction:status"),
                InlineKeyboardButton("Start", callback_data="svcaction:start"),
            ],
            [
                InlineKeyboardButton("Stop", callback_data="svcaction:stop"),
                InlineKeyboardButton("Restart", callback_data="svcaction:restart"),
            ],
            [
                InlineKeyboardButton("Logs", callback_data="svcaction:logs"),
                InlineKeyboardButton("Servicios", callback_data="svcpage:0"),
            ],
            [InlineKeyboardButton("Menu", callback_data="menu:main")],
        ]
    )


def service_page_keyboard(service_names: list[str], page: int) -> InlineKeyboardMarkup:
    total_pages = max(1, (len(service_names) + SERVICES_PER_PAGE - 1) // SERVICES_PER_PAGE)
    page = max(0, min(page, total_pages - 1))
    start = page * SERVICES_PER_PAGE
    rows = [
        [InlineKeyboardButton(name, callback_data=f"svcsel:{page}:{idx}")]
        for idx, name in enumerate(service_names[start : start + SERVICES_PER_PAGE])
    ]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("Anterior", callback_data=f"svcpage:{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("Siguiente", callback_data=f"svcpage:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("Menu", callback_data="menu:main")])
    return InlineKeyboardMarkup(rows)


def docker_page_keyboard(container_names: list[str], page: int) -> InlineKeyboardMarkup:
    total_pages = max(1, (len(container_names) + CONTAINERS_PER_PAGE - 1) // CONTAINERS_PER_PAGE)
    page = max(0, min(page, total_pages - 1))
    start = page * CONTAINERS_PER_PAGE
    rows = [
        [InlineKeyboardButton(name, callback_data=f"dockersel:{page}:{idx}")]
        for idx, name in enumerate(container_names[start : start + CONTAINERS_PER_PAGE])
    ]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("Anterior", callback_data=f"dockerpage:{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("Siguiente", callback_data=f"dockerpage:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("Menu", callback_data="menu:main")])
    return InlineKeyboardMarkup(rows)


def docker_action_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Start", callback_data="dockeraction:start"),
                InlineKeyboardButton("Stop", callback_data="dockeraction:stop"),
            ],
            [
                InlineKeyboardButton("Restart", callback_data="dockeraction:restart"),
                InlineKeyboardButton("Contenedores", callback_data="dockerpage:0"),
            ],
            [InlineKeyboardButton("Menu", callback_data="menu:main")],
        ]
    )


def configured_service_names() -> list[str]:
    if CONFIG.allow_all_systemd_services:
        return services.installed_services(CONFIG.command_timeout_seconds)
    return list(CONFIG.allowed_services)


async def show_main_menu(update: Update) -> None:
    await send_text(
        update,
        "Menu principal. Tambien puedes seguir usando comandos como /status o /service_restart nginx.",
        main_menu_keyboard(),
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
    await show_main_menu(update)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if not await require_authorized(update):
        return
    await send_text(update, help_text(), main_menu_keyboard())


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
    if not await require_authorized(update):
        return
    await show_docker_page(update, 0)


async def list_services(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if not await require_authorized(update):
        return
    text = await asyncio.to_thread(
        services.list_services,
        CONFIG.allowed_services,
        CONFIG.allow_all_systemd_services,
        CONFIG.command_timeout_seconds,
    )
    await send_text(update, text)


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
        args[0],
        CONFIG.allowed_services,
        CONFIG.allow_all_systemd_services,
        CONFIG.command_timeout_seconds,
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
        args[0],
        CONFIG.allowed_services,
        CONFIG.allow_all_systemd_services,
        CONFIG.command_timeout_seconds,
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


async def reply_callback(
    update: Update,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    if update.callback_query and update.callback_query.message:
        await update.callback_query.message.reply_text(text, reply_markup=reply_markup)


async def show_service_page(update: Update, page: int) -> None:
    service_names = await asyncio.to_thread(configured_service_names)
    if not service_names:
        await reply_callback(
            update,
            "No hay servicios disponibles. Revisa ALLOW_ALL_SYSTEMD_SERVICES o ALLOWED_SERVICES.",
            main_menu_keyboard(),
        )
        return
    service_names = sorted(service_names)
    total_pages = max(1, (len(service_names) + SERVICES_PER_PAGE - 1) // SERVICES_PER_PAGE)
    page = max(0, min(page, total_pages - 1))
    await reply_callback(
        update,
        f"Servicios systemd ({len(service_names)}). Pagina {page + 1}/{total_pages}.",
        service_page_keyboard(service_names, page),
    )


async def select_service(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str) -> None:
    try:
        _, page_raw, idx_raw = data.split(":", 2)
        page = int(page_raw)
        idx = int(idx_raw)
    except ValueError:
        await reply_callback(update, "Seleccion de servicio invalida.", main_menu_keyboard())
        return

    service_names = sorted(await asyncio.to_thread(configured_service_names))
    absolute_idx = page * SERVICES_PER_PAGE + idx
    if absolute_idx < 0 or absolute_idx >= len(service_names):
        await reply_callback(update, "Servicio fuera de rango.", main_menu_keyboard())
        return

    service = service_names[absolute_idx]
    valid, service_or_error = services.validate_service(
        service,
        CONFIG.allowed_services,
        CONFIG.allow_all_systemd_services,
        CONFIG.command_timeout_seconds,
    )
    if not valid:
        await reply_callback(update, service_or_error, main_menu_keyboard())
        return

    context.user_data["selected_service"] = service_or_error
    await reply_callback(
        update,
        f"Servicio seleccionado: {service_or_error}",
        service_action_keyboard(),
    )


async def show_docker_page(update: Update, page: int) -> None:
    container_names = await asyncio.to_thread(
        docker.list_container_names,
        CONFIG.command_timeout_seconds,
        CONFIG.max_telegram_message_length,
    )
    if not container_names:
        await reply_callback(
            update,
            "No hay contenedores Docker o no se pudieron listar. Revisa sudoers y Docker.",
            main_menu_keyboard(),
        )
        return
    container_names = sorted(container_names)
    total_pages = max(1, (len(container_names) + CONTAINERS_PER_PAGE - 1) // CONTAINERS_PER_PAGE)
    page = max(0, min(page, total_pages - 1))
    await reply_callback(
        update,
        f"Contenedores Docker ({len(container_names)}). Pagina {page + 1}/{total_pages}.",
        docker_page_keyboard(container_names, page),
    )


async def select_docker_container(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    data: str,
) -> None:
    try:
        _, page_raw, idx_raw = data.split(":", 2)
        page = int(page_raw)
        idx = int(idx_raw)
    except ValueError:
        await reply_callback(update, "Seleccion de contenedor invalida.", main_menu_keyboard())
        return

    container_names = sorted(
        await asyncio.to_thread(
            docker.list_container_names,
            CONFIG.command_timeout_seconds,
            CONFIG.max_telegram_message_length,
        )
    )
    absolute_idx = page * CONTAINERS_PER_PAGE + idx
    if absolute_idx < 0 or absolute_idx >= len(container_names):
        await reply_callback(update, "Contenedor fuera de rango.", main_menu_keyboard())
        return

    container = container_names[absolute_idx]
    valid, container_or_error = docker.validate_container_name(container)
    if not valid:
        await reply_callback(update, container_or_error, main_menu_keyboard())
        return

    context.user_data["selected_docker_container"] = container_or_error
    await reply_callback(
        update,
        f"Contenedor seleccionado: {container_or_error}",
        docker_action_keyboard(),
    )


async def execute_docker_button(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    action: str,
) -> None:
    container = context.user_data.get("selected_docker_container")
    if not isinstance(container, str) or not container:
        await reply_callback(
            update,
            "Primero selecciona un contenedor.",
            InlineKeyboardMarkup([[InlineKeyboardButton("Contenedores", callback_data="dockerpage:0")]]),
        )
        return

    valid, container_or_error = docker.validate_container_name(container)
    if not valid:
        await reply_callback(update, container_or_error, main_menu_keyboard())
        return
    container = container_or_error
    description = f"docker {action} {container}"

    def execute() -> system.CommandResult:
        return docker.container_action(
            action,
            container,
            CONFIG.command_timeout_seconds,
            CONFIG.max_telegram_message_length,
        )

    if action in {"stop", "restart"}:
        pending = CONFIRMATIONS.create(chat_id(update) or 0, description, execute)
        LOGGER.info("Confirmacion Docker creada para %s chat_id=%s", description, chat_id(update))
        await reply_callback(
            update,
            f"Accion peligrosa: {description}\n"
            f"Confirma en {CONFIG.confirm_ttl_seconds}s con:\n/confirm {pending.token}",
            docker_action_keyboard(),
        )
        return

    LOGGER.info("Ejecutando boton %s chat_id=%s", description, chat_id(update))
    result = await asyncio.to_thread(execute)
    await reply_callback(update, result.output, docker_action_keyboard())


async def execute_service_button(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    action: str,
) -> None:
    service = context.user_data.get("selected_service")
    if not isinstance(service, str) or not service:
        await reply_callback(update, "Primero selecciona un servicio.", InlineKeyboardMarkup(
            [[InlineKeyboardButton("Servicios", callback_data="svcpage:0")]]
        ))
        return

    valid, service_or_error = services.validate_service(
        service,
        CONFIG.allowed_services,
        CONFIG.allow_all_systemd_services,
        CONFIG.command_timeout_seconds,
    )
    if not valid:
        await reply_callback(update, service_or_error, main_menu_keyboard())
        return

    service = service_or_error
    description = f"systemctl {action} {service}"

    if action == "logs":
        LOGGER.info("Boton journalctl para %s chat_id=%s", service, chat_id(update))
        result = await asyncio.to_thread(
            services.logs,
            service,
            CONFIG.command_timeout_seconds,
            CONFIG.max_telegram_message_length,
        )
        await reply_callback(update, result.output, service_action_keyboard())
        return

    def execute() -> system.CommandResult:
        return services.systemctl(
            action,
            service,
            CONFIG.command_timeout_seconds,
            CONFIG.max_telegram_message_length,
        )

    if action in {"stop", "restart"}:
        pending = CONFIRMATIONS.create(chat_id(update) or 0, description, execute)
        LOGGER.info("Confirmacion creada desde boton para %s chat_id=%s", description, chat_id(update))
        await reply_callback(
            update,
            f"Accion peligrosa: {description}\n"
            f"Confirma en {CONFIG.confirm_ttl_seconds}s con:\n/confirm {pending.token}",
            service_action_keyboard(),
        )
        return

    LOGGER.info("Ejecutando boton %s chat_id=%s", description, chat_id(update))
    result = await asyncio.to_thread(execute)
    await reply_callback(update, result.output, service_action_keyboard())


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    await query.answer()
    if not is_authorized(update):
        LOGGER.warning("Acceso denegado callback chat_id=%s", chat_id(update))
        await reply_callback(update, "Acceso denegado.")
        return

    data = query.data or ""

    if data == "menu:main":
        await reply_callback(update, "Menu principal.", main_menu_keyboard())
        return
    if data == "menu:help":
        await reply_callback(update, help_text(), main_menu_keyboard())
        return
    if data == "menu:system":
        await reply_callback(update, "Sistema", system_menu_keyboard())
        return
    if data == "menu:updates":
        await reply_callback(update, "Actualizaciones y reinicio", updates_menu_keyboard())
        return
    if data.startswith("svcpage:"):
        try:
            page = int(data.split(":", 1)[1])
        except ValueError:
            page = 0
        await show_service_page(update, page)
        return
    if data.startswith("svcsel:"):
        await select_service(update, context, data)
        return
    if data.startswith("dockerpage:"):
        try:
            page = int(data.split(":", 1)[1])
        except ValueError:
            page = 0
        await show_docker_page(update, page)
        return
    if data.startswith("dockersel:"):
        await select_docker_container(update, context, data)
        return
    if data.startswith("dockeraction:"):
        action = data.split(":", 1)[1]
        if action not in {"start", "stop", "restart"}:
            await reply_callback(update, "Accion Docker invalida.", main_menu_keyboard())
            return
        await execute_docker_button(update, context, action)
        return
    if data.startswith("svcaction:"):
        action = data.split(":", 1)[1]
        if action not in {"status", "start", "stop", "restart", "logs"}:
            await reply_callback(update, "Accion de servicio invalida.", main_menu_keyboard())
            return
        await execute_service_button(update, context, action)
        return

    readonly_actions = {
        "act:status": ("status", system.status, system_menu_keyboard()),
        "act:ram": ("ram", system.ram, system_menu_keyboard()),
        "act:disk": ("disk", system.disk, system_menu_keyboard()),
        "act:ip": ("ip", system.local_ip, system_menu_keyboard()),
        "act:processes": ("processes", system.processes, system_menu_keyboard()),
        "act:updates": ("updates", updates.list_updates, updates_menu_keyboard()),
    }
    if data in readonly_actions:
        description, func, keyboard = readonly_actions[data]
        LOGGER.info("Ejecutando boton %s chat_id=%s", description, chat_id(update))
        result = await asyncio.to_thread(
            func,
            CONFIG.command_timeout_seconds,
            CONFIG.max_telegram_message_length,
        )
        await reply_callback(update, result.output, keyboard)
        return
    if data == "act:whoami":
        await reply_callback(update, f"Tu chat_id es: {chat_id(update)}", main_menu_keyboard())
        return
    if data == "danger:upgrade":
        def execute_upgrade() -> system.CommandResult:
            return updates.upgrade(
                CONFIG.command_timeout_seconds * 20,
                CONFIG.max_telegram_message_length,
            )

        pending = CONFIRMATIONS.create(chat_id(update) or 0, "apt upgrade -y", execute_upgrade)
        await reply_callback(
            update,
            f"Accion peligrosa: apt upgrade -y\n"
            f"Confirma en {CONFIG.confirm_ttl_seconds}s con:\n/confirm {pending.token}",
            updates_menu_keyboard(),
        )
        return
    if data == "danger:reboot":
        def execute_reboot() -> system.CommandResult:
            return system.run_command(
                ["sudo", "/usr/sbin/reboot"],
                timeout=CONFIG.command_timeout_seconds,
                max_chars=CONFIG.max_telegram_message_length,
            )

        pending = CONFIRMATIONS.create(chat_id(update) or 0, "reboot", execute_reboot)
        await reply_callback(
            update,
            f"Accion peligrosa: reiniciar el servidor\n"
            f"Confirma en {CONFIG.confirm_ttl_seconds}s con:\n/confirm {pending.token}",
            updates_menu_keyboard(),
        )
        return

    await reply_callback(update, "Boton no reconocido.", main_menu_keyboard())


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
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_error_handler(error_handler)
    return app


def main() -> None:
    setup_logging(CONFIG.log_file)
    LOGGER.info("Iniciando bot servicio=%s", CONFIG.service_name)
    build_application().run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
