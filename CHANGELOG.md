# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project follows semantic versioning once tagged releases exist.

## [Unreleased]

### Added

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

### Security

- No arbitrary command execution endpoint.
- No `shell=True` subprocess calls.
- Strict service-name validation.
- `.env` excluded from Git and installed with restricted permissions.
- Installed application code owned by root, with write access limited to logs.

## [0.1.0] - 2026-06-03

### Added

- First public-ready project structure.
