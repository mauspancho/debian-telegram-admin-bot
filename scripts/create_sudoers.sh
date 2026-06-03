#!/usr/bin/env bash
set -euo pipefail

BOT_USER="${1:-}"
SUDOERS_FILE="${2:-}"
SERVICES_CSV="${3:-}"
ALL_SERVICES_MARKER="__ALL_SYSTEMD_SERVICES__"

if [[ -z "$BOT_USER" || -z "$SUDOERS_FILE" ]]; then
  echo "Uso: $0 USUARIO /etc/sudoers.d/archivo servicios,separados,por,coma" >&2
  echo "O:   $0 USUARIO /etc/sudoers.d/archivo __ALL_SYSTEMD_SERVICES__" >&2
  exit 2
fi

if [[ ! "$BOT_USER" =~ ^[a-z_][a-z0-9_-]*[$]?$ ]]; then
  echo "Usuario Linux invalido: $BOT_USER" >&2
  exit 2
fi

if [[ ! "$SUDOERS_FILE" =~ ^/etc/sudoers\.d/[A-Za-z0-9_.-]+$ ]]; then
  echo "Ruta sudoers invalida: $SUDOERS_FILE" >&2
  exit 2
fi

trim() {
  local value="$1"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  printf '%s' "$value"
}

SERVICES=()

add_service() {
  local service="$1"
  local existing=""

  if [[ ! "$service" =~ ^[A-Za-z0-9][A-Za-z0-9_.@-]*$ ]]; then
    echo "Servicio invalido para sudoers: $service" >&2
    exit 2
  fi

  for existing in "${SERVICES[@]}"; do
    if [[ "$existing" == "$service" ]]; then
      return 0
    fi
  done
  SERVICES+=("$service")
}

if [[ "$SERVICES_CSV" == "$ALL_SERVICES_MARKER" ]]; then
  if ! command -v systemctl >/dev/null 2>&1; then
    echo "systemctl no esta disponible para enumerar servicios." >&2
    exit 1
  fi
  while read -r unit _rest; do
    [[ -z "${unit:-}" ]] && continue
    [[ "$unit" != *.service ]] && continue
    add_service "$unit"
  done < <(systemctl list-unit-files --type=service --no-legend --no-pager)
else
  IFS=',' read -r -a RAW_SERVICES <<< "$SERVICES_CSV"
  for raw in "${RAW_SERVICES[@]}"; do
    service="$(trim "$raw")"
    [[ -z "$service" ]] && continue
    add_service "$service"
  done
fi

if [[ "${#SERVICES[@]}" -eq 0 ]]; then
  echo "No se detectaron servicios para sudoers." >&2
  exit 2
fi

EMITTED_ALIASES=()

emit_alias_chunks() {
  local prefix="$1"
  shift
  local chunk=1
  local count=0
  local joined=""
  local alias_name=""
  local cmd=""

  for cmd in "$@"; do
    if [[ "$count" -eq 0 ]]; then
      alias_name="${prefix}_${chunk}"
      joined="$cmd"
    else
      joined+=", $cmd"
    fi
    count=$((count + 1))

    if [[ "$count" -ge 40 ]]; then
      echo "Cmnd_Alias ${alias_name} = ${joined}"
      EMITTED_ALIASES+=("$alias_name")
      chunk=$((chunk + 1))
      count=0
      joined=""
    fi
  done

  if [[ "$count" -gt 0 ]]; then
    echo "Cmnd_Alias ${alias_name} = ${joined}"
    EMITTED_ALIASES+=("$alias_name")
  fi
}

TMP_FILE="$(mktemp)"
trap 'rm -f "$TMP_FILE"' EXIT

{
  echo "# Generado por debian-telegram-admin-bot. No editar a mano."
  echo "Defaults:${BOT_USER} !requiretty"
  echo

  COMMAND_ALIASES=("DEBIAN_BOT_APT" "DEBIAN_BOT_REBOOT")

  systemctl_cmds=()
  journal_cmds=()
  for service in "${SERVICES[@]}"; do
    systemctl_cmds+=("/usr/bin/systemctl status ${service} --no-pager")
    systemctl_cmds+=("/usr/bin/systemctl start ${service}")
    systemctl_cmds+=("/usr/bin/systemctl stop ${service}")
    systemctl_cmds+=("/usr/bin/systemctl restart ${service}")
    journal_cmds+=("/usr/bin/journalctl -u ${service} -n 80 --no-pager")
  done

  emit_alias_chunks "DEBIAN_BOT_SYSTEMCTL" "${systemctl_cmds[@]}"
  emit_alias_chunks "DEBIAN_BOT_JOURNAL" "${journal_cmds[@]}"
  COMMAND_ALIASES=("${EMITTED_ALIASES[@]}" "${COMMAND_ALIASES[@]}")

  echo "Cmnd_Alias DEBIAN_BOT_APT = /usr/bin/apt update, /usr/bin/apt list --upgradable, /usr/bin/apt upgrade -y"
  echo "Cmnd_Alias DEBIAN_BOT_REBOOT = /usr/sbin/reboot"
  echo

  aliases_joined=""
  for alias_name in "${COMMAND_ALIASES[@]}"; do
    if [[ -n "$aliases_joined" ]]; then
      aliases_joined+=", "
    fi
    aliases_joined+="$alias_name"
  done
  echo "${BOT_USER} ALL=(root) NOPASSWD: ${aliases_joined}"
} > "$TMP_FILE"

chmod 0440 "$TMP_FILE"
if ! visudo -cf "$TMP_FILE" >/dev/null; then
  echo "El archivo sudoers generado no es valido." >&2
  exit 1
fi

install -o root -g root -m 0440 "$TMP_FILE" "$SUDOERS_FILE"
visudo -cf "$SUDOERS_FILE" >/dev/null
echo "Sudoers instalado en $SUDOERS_FILE con ${#SERVICES[@]} servicios."
