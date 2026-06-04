# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project follows semantic versioning once tagged releases exist.

## [Unreleased]

### Added

- Monitoring module with `/report`, `/security_check`, and `/disk_alerts`.
- Backup module with `.env` defined targets, `/backup_list`, `/backup_create`, and confirmation-gated `/backup_restore`.
- Multi-role authorization with `AUTHORIZED_CHAT_IDS`, `ADMIN_CHAT_IDS`, and `READONLY_CHAT_IDS`.
- Docker logs and stats commands with strict container-name validation.
- Bot version and controlled self-update commands for local Git installations.
- Administrative audit log at `logs/audit.log`.
- Initial Telegram polling bot for Debian administration.
- Interactive `install.sh` and `uninstall.sh`.
- Dedicated Linux user support.
- `.env` based configuration.
- Authorized `chat_id` validation.
- Service whitelist for systemd commands.
- Two-step confirmation flow for dangerous actions.
- Sudoers generator with command-specific permissions.
- Local rotating logs.
- GitHub-ready documentation and community files.
- Optional `ALLOW_ALL_SYSTEMD_SERVICES=true` mode to control installed systemd services without listing each service manually.

### Security

- No arbitrary command execution endpoint.
- No `shell=True` subprocess calls.
- Strict service-name validation.
- Strict Docker container-name validation.
- Backup commands do not accept arbitrary paths from Telegram.
- Stop, restart, reboot, upgrade, restore, and bot update actions require confirmation.
- `.env` excluded from Git and installed with restricted permissions.
- Installed application code owned by root, with write access limited to logs.

## [0.1.0] - 2026-06-03

### Added

- First public-ready project structure.
