#!/usr/bin/env bash
set -euo pipefail

DEFAULT_INSTALL_PATH="/opt/debian-telegram-admin-bot"
DEFAULT_SERVICE_NAME="debian-telegram-admin-bot"
DEFAULT_BOT_USER="debianbot"
SUDOERS_NAME="debian-telegram-admin-bot"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    echo "Ejecuta este instalador como root: sudo ./install.sh" >&2
    exit 1
  fi
}

require_debian_like() {
  if [[ ! -r /etc/os-release ]]; then
    echo "No se pudo leer /etc/os-release" >&2
    exit 1
  fi
  # shellcheck disable=SC1091
  . /etc/os-release
  local id_like="${ID_LIKE:-}"
  if [[ "${ID:-}" != "debian" && "$id_like" != *"debian"* ]]; then
    echo "Este instalador esta pensado para Debian o derivados." >&2
    exit 1
  fi
}

prompt() {
  local label="$1"
  local default="$2"
  local value
  read -r -p "$label [$default]: " value
  echo "${value:-$default}"
}

prompt_secret() {
  local label="$1"
  local value
  read -r -s -p "$label: " value
  echo >&2
  echo "$value"
}

validate_service_csv() {
  local csv="$1"
  IFS=',' read -r -a services <<< "$csv"
  for raw in "${services[@]}"; do
    service="${raw#"${raw%%[![:space:]]*}"}"
    service="${service%"${service##*[![:space:]]}"}"
    [[ -z "$service" ]] && continue
    if [[ ! "$service" =~ ^[A-Za-z0-9][A-Za-z0-9_.@-]*$ ]]; then
      echo "Servicio invalido: $service" >&2
      exit 1
    fi
  done
}

validate_install_path() {
  local path="$1"
  if [[ ! "$path" =~ ^/[A-Za-z0-9._/@+-]+$ ]]; then
    echo "Ruta de instalacion invalida. Usa una ruta absoluta sin espacios." >&2
    exit 1
  fi
  if [[ "$path" == "/" || "$path" == *"/../"* || "$path" == */.. || "$path" == */. ]]; then
    echo "Ruta de instalacion insegura: $path" >&2
    exit 1
  fi
}

install_dependencies() {
  apt-get update
  apt-get install -y python3 python3-venv python3-pip sudo ca-certificates
}

create_bot_user() {
  local user="$1"
  local install_path="$2"
  if id "$user" >/dev/null 2>&1; then
    echo "El usuario $user ya existe."
    return
  fi
  useradd --system --user-group --home-dir "$install_path" --shell /usr/sbin/nologin "$user"
}

ensure_bot_group() {
  local user="$1"
  local group="$2"
  if ! getent group "$group" >/dev/null 2>&1; then
    groupadd --system "$group"
  fi
  usermod -a -G "$group" "$user"
}

copy_project() {
  local install_path="$1"
  install -d -o root -g root -m 0755 "$install_path"

  if [[ "$(cd "$SCRIPT_DIR" && pwd)" != "$(cd "$install_path" 2>/dev/null && pwd || true)" ]]; then
    cp -a "$SCRIPT_DIR/bot.py" "$install_path/"
    cp -a "$SCRIPT_DIR/config.py" "$install_path/"
    cp -a "$SCRIPT_DIR/requirements.txt" "$install_path/"
    cp -a "$SCRIPT_DIR/.env.example" "$install_path/"
    for doc_file in README.md LICENSE CHANGELOG.md SECURITY.md CONTRIBUTING.md; do
      cp -a "$SCRIPT_DIR/$doc_file" "$install_path/" 2>/dev/null || true
    done
    cp -a "$SCRIPT_DIR/modules" "$install_path/"
    cp -a "$SCRIPT_DIR/scripts" "$install_path/"
    cp -a "$SCRIPT_DIR/uninstall.sh" "$install_path/" 2>/dev/null || true
    cp -a "$SCRIPT_DIR/install.sh" "$install_path/" 2>/dev/null || true
  fi
}

write_env() {
  local env_file="$1"
  local token="$2"
  local chat_id="$3"
  local registration_mode="$4"
  local services="$5"
  local service_name="$6"
  local install_path="$7"

  umask 077
  cat > "$env_file" <<EOF
TELEGRAM_BOT_TOKEN=$token
AUTHORIZED_CHAT_ID=$chat_id
REGISTRATION_MODE=$registration_mode
ALLOWED_SERVICES=$services
SERVICE_NAME=$service_name
INSTALL_PATH=$install_path
LOG_FILE=$install_path/logs/bot.log
CONFIRM_TTL_SECONDS=180
COMMAND_TIMEOUT_SECONDS=30
MAX_TELEGRAM_MESSAGE_LENGTH=3500
EOF
}

write_systemd_unit() {
  local unit_file="$1"
  local service_name="$2"
  local bot_user="$3"
  local install_path="$4"

  cat > "$unit_file" <<EOF
[Unit]
Description=Debian Telegram Admin Bot
Documentation=file://$install_path/README.md
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$bot_user
Group=$bot_user
WorkingDirectory=$install_path
Environment=PYTHONUNBUFFERED=1
ExecStart=$install_path/venv/bin/python $install_path/bot.py
Restart=on-failure
RestartSec=5
PrivateTmp=true
ProtectHome=true
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX

[Install]
WantedBy=multi-user.target
EOF
  chmod 0644 "$unit_file"
}

main() {
  require_root
  require_debian_like

  echo "Instalador de debian-telegram-admin-bot"
  token="$(prompt_secret "Token de Telegram")"
  if [[ -z "$token" ]]; then
    echo "El token es obligatorio." >&2
    exit 1
  fi

  read -r -p "Chat ID autorizado (deja vacio para modo registro temporal): " chat_id
  registration_mode="false"
  if [[ -z "$chat_id" ]]; then
    registration_mode="true"
    echo "Modo registro temporal activado. Solo /whoami estara disponible."
  elif [[ ! "$chat_id" =~ ^-?[0-9]+$ ]]; then
    echo "El chat_id debe ser numerico." >&2
    exit 1
  fi

  read -r -p "Servicios permitidos separados por coma [palworld,docker,ssh]: " services
  services="${services:-palworld,docker,ssh}"
  validate_service_csv "$services"

  install_path="$(prompt "Ruta de instalacion" "$DEFAULT_INSTALL_PATH")"
  service_name="$(prompt "Nombre del servicio systemd" "$DEFAULT_SERVICE_NAME")"
  bot_user="$(prompt "Usuario Linux que ejecutara el bot" "$DEFAULT_BOT_USER")"

  validate_install_path "$install_path"

  if [[ ! "$service_name" =~ ^[A-Za-z0-9][A-Za-z0-9_.@-]*$ ]]; then
    echo "Nombre de servicio systemd invalido: $service_name" >&2
    exit 1
  fi
  if [[ ! "$bot_user" =~ ^[a-z_][a-z0-9_-]*[$]?$ ]]; then
    echo "Usuario Linux invalido: $bot_user" >&2
    exit 1
  fi

  install_dependencies
  create_bot_user "$bot_user" "$install_path"
  ensure_bot_group "$bot_user" "$bot_user"
  copy_project "$install_path"

  python3 -m venv "$install_path/venv"
  "$install_path/venv/bin/python" -m pip install --upgrade pip
  "$install_path/venv/bin/pip" install -r "$install_path/requirements.txt"

  write_env "$install_path/.env" "$token" "$chat_id" "$registration_mode" "$services" "$service_name" "$install_path"
  chown -R root:root "$install_path"
  install -d -o "$bot_user" -g "$bot_user" -m 0750 "$install_path/logs"
  chown root:"$bot_user" "$install_path/.env"
  chmod 0640 "$install_path/.env"
  chmod 0755 "$install_path"
  chmod +x "$install_path/install.sh" "$install_path/uninstall.sh" "$install_path/scripts/"*.sh

  "$install_path/scripts/create_sudoers.sh" "$bot_user" "/etc/sudoers.d/$SUDOERS_NAME" "$services"
  visudo -c >/dev/null

  write_systemd_unit "/etc/systemd/system/${service_name}.service" "$service_name" "$bot_user" "$install_path"
  systemctl daemon-reload
  systemctl enable --now "${service_name}.service"

  "$install_path/scripts/validate_install.sh" "$install_path"

  echo
  echo "Instalacion completada."
  echo "Servicio: ${service_name}.service"
  echo "Logs: journalctl -u ${service_name}.service -f"
  if [[ "$registration_mode" == "true" ]]; then
    echo "Ejecuta /whoami en Telegram, edita $install_path/.env y reinicia con:"
    echo "systemctl restart ${service_name}.service"
  fi
}

main "$@"
