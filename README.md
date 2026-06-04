# Debian Telegram Admin Bot

Bot de Telegram para administrar tareas concretas de un servidor Debian 12/13 de forma segura, sin abrir puertos y sin permitir comandos arbitrarios.

> Estado del proyecto: primera version funcional orientada a servidores personales o pequenos despliegues. Revisa `SECURITY.md` antes de usarlo en produccion.

## Caracteristicas

- Telegram en modo polling, sin webhooks ni puertos entrantes.
- Configuracion por `.env`, sin tokens hardcodeados.
- Acceso limitado por `chat_id`, con roles admin y readonly.
- Usuario Linux dedicado, por defecto `debianbot`.
- Sudoers generado con comandos concretos, no sudo global.
- Lista blanca de servicios systemd permitidos.
- Confirmacion en dos pasos para acciones peligrosas.
- Validacion estricta de nombres de servicios.
- Monitoreo basico con reporte general, chequeo de seguridad y alertas de disco.
- Backups por targets definidos en `.env`, sin rutas arbitrarias desde Telegram.
- Logs y estadisticas Docker con validacion estricta de contenedores.
- Autoactualizacion controlada del bot cuando la instalacion tiene repo Git.
- Auditoria de acciones administrativas en `logs/audit.log`.
- Salida recortada para evitar mensajes demasiado grandes.
- Logs locales rotativos y logs via `journalctl`.
- Instalador y desinstalador interactivos.
- Menu interactivo con botones de Telegram desde `/start`.
- Menu nativo de comandos de Telegram, accesible con `/menu` o desde el boton de comandos del cliente cuando este disponible.

## Instalacion rapida

En un servidor Debian 12/13 o derivado:

```bash
git clone https://github.com/mauspancho/debian-telegram-admin-bot.git
cd debian-telegram-admin-bot
sudo bash install.sh
```

El instalador preguntara:

- Token del bot de Telegram.
- `chat_id` admin autorizado.
- `chat_id` readonly opcionales, separados por coma.
- Si quieres permitir controlar todos los servicios systemd instalados.
- Servicios permitidos, por ejemplo `ssh,nginx,docker`.
- Ruta de instalacion, por defecto `/opt/debian-telegram-admin-bot`.
- Nombre del servicio systemd, por defecto `debian-telegram-admin-bot`.
- Usuario Linux que ejecutara el bot, por defecto `debianbot`.

Si no conoces tu `chat_id`, deja ese campo vacio durante la instalacion. El bot quedara en modo registro temporal para responder a `/whoami`.

## Crear el bot en BotFather

1. Abre Telegram y escribe a `@BotFather`.
2. Ejecuta `/newbot`.
3. Elige un nombre visible.
4. Elige un username terminado en `bot`.
5. Copia el token entregado por BotFather.
6. Usa ese token solo durante la instalacion o en tu `.env` local.

No publiques el token en GitHub, issues, capturas, logs ni mensajes de soporte.

## Obtener el chat_id

Opcion recomendada:

1. Instala dejando vacio el campo `Chat ID autorizado`.
2. Escribe `/whoami` al bot desde Telegram.
3. Copia el numero que responde.
4. Edita el archivo de configuracion:

```bash
sudo nano /opt/debian-telegram-admin-bot/.env
```

5. Configura:

```env
AUTHORIZED_CHAT_IDS=123456789
ADMIN_CHAT_IDS=123456789
READONLY_CHAT_IDS=
REGISTRATION_MODE=false
```

6. Reinicia:

```bash
sudo systemctl restart debian-telegram-admin-bot.service
```

## Tabla de comandos

Tambien puedes usar el menu con botones ejecutando `/start` o `/menu`. Al iniciar, el bot registra los comandos iniciales para que Telegram los muestre en el boton nativo de comandos del campo de escritura cuando el cliente lo soporte.

| Comando | Descripcion | Requiere confirmacion |
| --- | --- | --- |
| `/start` | Muestra ayuda basica | No |
| `/help` | Lista comandos disponibles | No |
| `/whoami` | Muestra el `chat_id` del usuario | No |
| `/status` | Hostname, kernel, uptime y carga | No |
| `/ram` | Uso de memoria | No |
| `/disk` | Uso de disco con `df -h` | No |
| `/ip` | IP local del servidor | No |
| `/services` | Lista servicios permitidos | No |
| `/service_status nombre` | Estado systemd de un servicio permitido | No |
| `/service_start nombre` | Inicia un servicio permitido | No |
| `/service_stop nombre` | Detiene un servicio permitido | Si |
| `/service_restart nombre` | Reinicia un servicio permitido | Si |
| `/service_logs nombre` | Ultimas 80 lineas de `journalctl -u` | No |
| `/processes` | Procesos principales por CPU, sin argumentos completos | No |
| `/docker_ps` | Abre botones con los contenedores Docker | No |
| `/docker_logs contenedor` | Muestra logs recientes de un contenedor validado | No |
| `/docker_stats` | Muestra uso instantaneo de contenedores Docker | No |
| `/report` | Resumen general del servidor | No |
| `/security_check` | Revisa permisos, usuario, `.env` y sudoers | No |
| `/disk_alerts` | Muestra discos con uso alto | No |
| `/backup_list` | Lista targets y backups disponibles | No |
| `/backup_create nombre` | Crea backup de un target definido en `.env` | No |
| `/backup_restore nombre` | Restaura el ultimo backup del target definido | Si |
| `/bot_version` | Muestra version del bot | No |
| `/bot_update_check` | Revisa estado Git del bot instalado | No |
| `/bot_update` | Ejecuta `git pull --ff-only` en el repo permitido | Si |
| `/updates` | Ejecuta `apt update` y lista paquetes actualizables | No |
| `/upgrade_confirm` | Solicita confirmacion para `apt upgrade -y` | Si |
| `/reboot_confirm` | Solicita confirmacion para reiniciar el servidor | Si |
| `/confirm TOKEN` | Ejecuta una accion pendiente | No aplica |

## Capturas de ejemplo en texto

Ejemplo de `/status`:

```text
Usuario:
/status

Bot:
Hostname: debian-server
Kernel: 6.1.0-18-amd64
Uptime: up 3 days, 4 hours, 12 minutes
Carga: 0.08 0.04 0.01 1/231 4921
```

Ejemplo de confirmacion:

```text
Usuario:
/service_restart nginx

Bot:
Accion peligrosa: systemctl restart nginx
Confirma en 180s con:
/confirm a1b2c3d4

Usuario:
/confirm a1b2c3d4

Bot:
Ejecutando: systemctl restart nginx
(sin salida)
```

Ejemplo de acceso denegado:

```text
Usuario no autorizado:
/ram

Bot:
Acceso denegado.
```

## Estructura del proyecto

```text
debian-telegram-admin-bot/
|-- bot.py
|-- config.py
|-- requirements.txt
|-- .env.example
|-- .gitignore
|-- install.sh
|-- uninstall.sh
|-- README.md
|-- LICENSE
|-- CHANGELOG.md
|-- SECURITY.md
|-- CONTRIBUTING.md
|-- scripts/
|   |-- create_sudoers.sh
|   `-- validate_install.sh
`-- modules/
    |-- system.py
    |-- services.py
    |-- docker.py
    |-- updates.py
    |-- monitoring.py
    |-- backups.py
    |-- bot_update.py
    `-- security.py
```

## Configuracion

El instalador genera `/opt/debian-telegram-admin-bot/.env`. Tambien puedes usar `.env.example` como base:

```bash
cp .env.example .env
```

Variables principales:

```env
TELEGRAM_BOT_TOKEN=REEMPLAZA_CON_TOKEN_DE_BOTFATHER
AUTHORIZED_CHAT_IDS=123456789
ADMIN_CHAT_IDS=123456789
READONLY_CHAT_IDS=
REGISTRATION_MODE=false
ALLOWED_SERVICES=ssh,nginx
SERVICE_NAME=debian-telegram-admin-bot
INSTALL_PATH=/opt/debian-telegram-admin-bot
LOG_FILE=/opt/debian-telegram-admin-bot/logs/bot.log
AUDIT_LOG_FILE=/opt/debian-telegram-admin-bot/logs/audit.log
BACKUP_TARGETS=etc-nginx:/etc/nginx
BACKUP_PATH=/opt/debian-telegram-admin-bot/backups
BOT_REPO_PATH=
CONFIRM_TTL_SECONDS=180
COMMAND_TIMEOUT_SECONDS=30
MAX_TELEGRAM_MESSAGE_LENGTH=3500
```

## Roles

`ADMIN_CHAT_IDS` puede consultar y ejecutar acciones con confirmacion. `READONLY_CHAT_IDS` solo puede usar comandos de consulta como estado, disco, logs, reportes, backups listados y version del bot. `AUTHORIZED_CHAT_IDS` debe contener la union de ambos roles. La variable antigua `AUTHORIZED_CHAT_ID` se acepta por compatibilidad, pero no es la forma recomendada para instalaciones nuevas.

## Backups

Los backups no aceptan rutas desde Telegram. Define nombres permitidos en `.env`:

```env
BACKUP_TARGETS=nginx:/etc/nginx,app:/srv/app/config
BACKUP_PATH=/opt/debian-telegram-admin-bot/backups
```

Despues usa `/backup_create nginx`, `/backup_list` y `/backup_restore nginx`. La restauracion siempre requiere `/confirm TOKEN` y necesita que el usuario del bot tenga permisos de escritura sobre el destino.

## Autoactualizacion

`/bot_update_check` y `/bot_update` solo funcionan si `INSTALL_PATH` contiene una carpeta `.git` o si defines `BOT_REPO_PATH` apuntando a un repo Git local. `/bot_update` usa `git pull --ff-only` y requiere confirmacion. No se ejecutan comandos arbitrarios ni scripts remotos.

## Agregar servicios permitidos

Edita `.env`:

```bash
sudo nano /opt/debian-telegram-admin-bot/.env
```

Ajusta la lista:

```env
ALLOWED_SERVICES=ssh,nginx,docker
```

Regenera sudoers para que los permisos del sistema coincidan:

```bash
sudo /opt/debian-telegram-admin-bot/scripts/create_sudoers.sh \
  debianbot \
  /etc/sudoers.d/debian-telegram-admin-bot \
  "ssh,nginx,docker"

sudo visudo -c
sudo systemctl restart debian-telegram-admin-bot.service
```

El nombre del servicio debe empezar con letra o numero y solo puede contener letras, numeros, `_`, `-`, `.`, o `@`.

## Permitir todos los servicios systemd

Si quieres que el bot pueda ver estado, iniciar, detener y reiniciar cualquier servicio systemd instalado en Debian, activa el modo amplio:

```bash
sudo nano /opt/debian-telegram-admin-bot/.env
```

Configura:

```env
ALLOW_ALL_SYSTEMD_SERVICES=true
ALLOWED_SERVICES=
```

Despues regenera sudoers con la marca especial que enumera los servicios instalados:

```bash
sudo bash /opt/debian-telegram-admin-bot/scripts/create_sudoers.sh \
  debianbot \
  /etc/sudoers.d/debian-telegram-admin-bot \
  "__ALL_SYSTEMD_SERVICES__"

sudo visudo -c
sudo systemctl restart debian-telegram-admin-bot.service
```

En este modo puedes usar comandos como:

```text
/service_status nginx
/service_restart apache2
/service_stop docker
/service_start ssh
```

Si instalas servicios nuevos despues, vuelve a ejecutar `create_sudoers.sh` con `__ALL_SYSTEMD_SERVICES__` para que sudoers incluya las nuevas unidades.

## Logs

Logs del servicio systemd:

```bash
sudo journalctl -u debian-telegram-admin-bot.service -f
```

Log local rotativo:

```bash
sudo tail -f /opt/debian-telegram-admin-bot/logs/bot.log
```

Estado del servicio:

```bash
sudo systemctl status debian-telegram-admin-bot.service
```

## Hardening recomendado

- Usa un bot de Telegram dedicado solo para este servidor.
- No agregues el usuario `debianbot` al grupo `docker` salvo que aceptes el riesgo equivalente a root.
- Manten corta la lista `ALLOWED_SERVICES`.
- Evita permitir servicios criticos que no necesitas administrar por Telegram.
- Usa un `chat_id` de usuario privado, no de grupos, salvo que entiendas el riesgo operativo.
- Protege tu cuenta de Telegram con 2FA.
- Revisa periodicamente `/etc/sudoers.d/debian-telegram-admin-bot`.
- Revisa `logs/audit.log` despues de cada accion administrativa.
- Manten `BACKUP_TARGETS` con rutas minimas y revisadas.
- Manten Debian actualizado.
- Rota el token en BotFather si sospechas exposicion.
- No publiques `.env`, logs reales ni capturas con datos sensibles.

## Solucion de problemas

### El bot no responde

```bash
sudo systemctl status debian-telegram-admin-bot.service
sudo journalctl -u debian-telegram-admin-bot.service -n 100 --no-pager
```

Verifica que el token sea correcto y que el servidor tenga salida a Internet.

### Recibo "Acceso denegado"

Comprueba `AUTHORIZED_CHAT_IDS`, `ADMIN_CHAT_IDS` y `READONLY_CHAT_IDS`:

```bash
sudo grep -E 'AUTHORIZED_CHAT_IDS|ADMIN_CHAT_IDS|READONLY_CHAT_IDS' /opt/debian-telegram-admin-bot/.env
```

Si instalaste en modo registro temporal, ejecuta `/whoami`, actualiza `.env`, agrega tu chat a `AUTHORIZED_CHAT_IDS` y `ADMIN_CHAT_IDS`, y cambia `REGISTRATION_MODE=false`.

### Un servicio aparece como no permitido

Comprueba que el nombre este en `.env` y en sudoers:

```bash
sudo grep ALLOWED_SERVICES /opt/debian-telegram-admin-bot/.env
sudo cat /etc/sudoers.d/debian-telegram-admin-bot
```

Despues regenera sudoers y reinicia el servicio.

### Sudo pide password o falla

Valida sudoers:

```bash
sudo visudo -c
sudo -l -U debianbot
```

Comprueba que el comando solicitado coincide exactamente con lo generado en `/etc/sudoers.d/debian-telegram-admin-bot`.

### Docker no lista contenedores

El boton `Docker` del menu y el comando `/docker_ps` muestran todos los contenedores en una sola lista de botones, usando solo el nombre de cada contenedor. Al seleccionar uno, aparecen acciones:

- `Start`
- `Stop`
- `Restart`

`Stop` y `Restart` piden confirmacion con `/confirm TOKEN`.

Docker usa sudoers limitado para ejecutar solo:

```bash
/usr/bin/docker ps *
/usr/bin/docker start *
/usr/bin/docker stop *
/usr/bin/docker restart *
/usr/bin/docker logs *
/usr/bin/docker stats *
```

Si venias de una instalacion anterior y recibes permiso denegado contra `/var/run/docker.sock`, regenera sudoers:

```bash
sudo bash /opt/debian-telegram-admin-bot/scripts/create_sudoers.sh \
  debianbot \
  /etc/sudoers.d/debian-telegram-admin-bot \
  "__ALL_SYSTEMD_SERVICES__"

sudo visudo -c
sudo systemctl restart debian-telegram-admin-bot.service
```

No agregues `debianbot` al grupo `docker` salvo que aceptes el riesgo equivalente a root.

### `apt upgrade` tarda demasiado

El comando se ejecuta con timeout ampliado. Si el sistema tiene muchas actualizaciones, revisa manualmente:

```bash
sudo journalctl -u debian-telegram-admin-bot.service -f
```

## Desinstalacion

```bash
sudo bash /opt/debian-telegram-admin-bot/uninstall.sh
```

El desinstalador elimina el servicio systemd, el archivo sudoers y pregunta antes de borrar archivos o usuario Linux.

## Seguridad

Lee [SECURITY.md](SECURITY.md) para conocer el modelo de seguridad, riesgos aceptados y como reportar vulnerabilidades.

Resumen:

- No hay comando libre.
- No se usa `shell=True`.
- Las acciones peligrosas requieren confirmacion.
- El bot no corre como root.
- El token vive en `.env`, que no debe subirse a GitHub.

## Contribuir

Lee [CONTRIBUTING.md](CONTRIBUTING.md) antes de abrir issues o pull requests.

## Licencia

MIT. Ver [LICENSE](LICENSE).
