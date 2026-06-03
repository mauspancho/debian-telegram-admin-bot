#!/usr/bin/env bash
set -euo pipefail

BOT_USER="${1:-}"
SUDOERS_FILE="${2:-}"
SERVICES_CSV="${3:-}"

if [[ -z "$BOT_USER" || -z "$SUDOERS_FILE" ]]; then
  echo "Uso: $0 USUARIO /etc/sudoers.d/archivo servicios,separados,por,coma" >&2
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

IFS=',' read -r -a RAW_SERVICES <<< "$SERVICES_CSV"
SERVICES=()
for raw in "${RAW_SERVICES[@]}"; do
  service="$(trim "$raw")"
  [[ -z "$service" ]] && continue
  if [[ ! "$service" =~ ^[A-Za-z0-9][A-Za-z0-9_.@-]*$ ]]; then
    echo "Servicio invalido para sudoers: $service" >&2
    exit 2
  fi
  duplicate="false"
  for existing in "${SERVICES[@]}"; do
    if [[ "$existing" == "$service" ]]; then
      duplicate="true"
      break
    fi
  done
  [[ "$duplicate" == "true" ]] && continue
  SERVICES+=("$service")
done

TMP_FILE="$(mktemp)"
trap 'rm -f "$TMP_FILE"' EXIT

{
  echo "# Generado por debian-telegram-admin-bot. No editar a mano."
  echo "Defaults:${BOT_USER} !requiretty"
  echo

  COMMAND_ALIASES=("DEBIAN_BOT_APT" "DEBIAN_BOT_REBOOT")

  if [[ "${#SERVICES[@]}" -gt 0 ]]; then
    systemctl_cmds=()
    journal_cmds=()
    for service in "${SERVICES[@]}"; do
      systemctl_cmds+=("/usr/bin/systemctl status ${service} --no-pager")
      systemctl_cmds+=("/usr/bin/systemctl start ${service}")
      systemctl_cmds+=("/usr/bin/systemctl stop ${service}")
      systemctl_cmds+=("/usr/bin/systemctl restart ${service}")
      journal_cmds+=("/usr/bin/journalctl -u ${service} -n 80 --no-pager")
    done
    printf 'Cmnd_Alias DEBIAN_BOT_SYSTEMCTL = '
    local_joined=""
    for cmd in "${systemctl_cmds[@]}"; do
      if [[ -n "$local_joined" ]]; then
        local_joined+=", "
      fi
      local_joined+="$cmd"
    done
    echo "$local_joined"

    printf 'Cmnd_Alias DEBIAN_BOT_JOURNAL = '
    local_joined=""
    for cmd in "${journal_cmds[@]}"; do
      if [[ -n "$local_joined" ]]; then
        local_joined+=", "
      fi
      local_joined+="$cmd"
    done
    echo "$local_joined"
    COMMAND_ALIASES=("DEBIAN_BOT_SYSTEMCTL" "DEBIAN_BOT_JOURNAL" "${COMMAND_ALIASES[@]}")
  fi

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
echo "Sudoers instalado en $SUDOERS_FILE"
