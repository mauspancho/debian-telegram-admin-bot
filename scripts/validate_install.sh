#!/usr/bin/env bash
set -euo pipefail

INSTALL_PATH="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

echo "Validando instalacion en $INSTALL_PATH"

required_files=(
  "$INSTALL_PATH/bot.py"
  "$INSTALL_PATH/config.py"
  "$INSTALL_PATH/requirements.txt"
  "$INSTALL_PATH/.env"
  "$INSTALL_PATH/modules/system.py"
  "$INSTALL_PATH/modules/services.py"
  "$INSTALL_PATH/modules/docker.py"
  "$INSTALL_PATH/modules/updates.py"
  "$INSTALL_PATH/modules/security.py"
)

for file in "${required_files[@]}"; do
  if [[ ! -f "$file" ]]; then
    echo "Falta archivo requerido: $file" >&2
    exit 1
  fi
done

if [[ ! -x "$INSTALL_PATH/venv/bin/python" ]]; then
  echo "No existe el Python del venv: $INSTALL_PATH/venv/bin/python" >&2
  exit 1
fi

"$INSTALL_PATH/venv/bin/python" -m py_compile \
  "$INSTALL_PATH/bot.py" \
  "$INSTALL_PATH/config.py" \
  "$INSTALL_PATH/modules/system.py" \
  "$INSTALL_PATH/modules/services.py" \
  "$INSTALL_PATH/modules/docker.py" \
  "$INSTALL_PATH/modules/updates.py" \
  "$INSTALL_PATH/modules/security.py"

echo "Validacion completada."
