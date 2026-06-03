#!/usr/bin/env bash
set -euo pipefail

DEFAULT_INSTALL_PATH="/opt/debian-telegram-admin-bot"
DEFAULT_SERVICE_NAME="debian-telegram-admin-bot"
DEFAULT_BOT_USER="debianbot"
SUDOERS_NAME="debian-telegram-admin-bot"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Ejecuta este desinstalador como root: sudo ./uninstall.sh" >&2
  exit 1
fi

prompt() {
  local label="$1"
  local default="$2"
  local value
  read -r -p "$label [$default]: " value
  echo "${value:-$default}"
}

validate_service_name() {
  local value="$1"
  if [[ ! "$value" =~ ^[A-Za-z0-9][A-Za-z0-9_.@-]*$ ]]; then
    echo "Nombre de servicio systemd invalido: $value" >&2
    exit 1
  fi
}

validate_user_name() {
  local value="$1"
  if [[ ! "$value" =~ ^[a-z_][a-z0-9_-]*[$]?$ ]]; then
    echo "Usuario Linux invalido: $value" >&2
    exit 1
  fi
}

safe_install_path() {
  local value="$1"
  local resolved
  if [[ ! "$value" =~ ^/[A-Za-z0-9._/@+-]+$ ]]; then
    return 1
  fi
  resolved="$(realpath -m "$value")"
  [[ "$resolved" == /opt/* && "$resolved" != "/opt" && "$resolved" != "/opt/" && -d "$resolved" ]]
}

service_name="$(prompt "Nombre del servicio systemd" "$DEFAULT_SERVICE_NAME")"
install_path="$(prompt "Ruta de instalacion" "$DEFAULT_INSTALL_PATH")"
bot_user="$(prompt "Usuario Linux del bot" "$DEFAULT_BOT_USER")"

validate_service_name "$service_name"
validate_user_name "$bot_user"

unit_file="/etc/systemd/system/${service_name}.service"
sudoers_file="/etc/sudoers.d/$SUDOERS_NAME"

if systemctl list-unit-files "${service_name}.service" >/dev/null 2>&1; then
  systemctl disable --now "${service_name}.service" >/dev/null 2>&1 || true
fi

if [[ -f "$unit_file" ]]; then
  rm -f "$unit_file"
  systemctl daemon-reload
fi

if [[ -f "$sudoers_file" ]]; then
  rm -f "$sudoers_file"
  visudo -c >/dev/null
fi

if safe_install_path "$install_path"; then
  install_path="$(realpath -m "$install_path")"
  read -r -p "Eliminar archivos en $install_path? [s/N]: " remove_files
  if [[ "$remove_files" =~ ^[sSyY]$ ]]; then
    rm -rf "$install_path"
  fi
else
  echo "No se elimina la ruta por seguridad: $install_path"
fi

if id "$bot_user" >/dev/null 2>&1; then
  read -r -p "Eliminar usuario $bot_user? [s/N]: " remove_user
  if [[ "$remove_user" =~ ^[sSyY]$ ]]; then
    userdel "$bot_user"
  fi
fi

echo "Desinstalacion completada."
