# Security Policy

## Supported versions

This project is in its first public-ready stage. Until stable releases are tagged, security fixes are applied to the default branch.

| Version | Supported |
| --- | --- |
| `main` | Yes |
| Tagged releases | Not yet |

## Security model

The bot is designed for a narrow administration surface:

- Telegram polling only; no inbound HTTP port is opened by the bot.
- One authorized Telegram `chat_id`.
- No generic shell command endpoint.
- Only pre-defined Python handlers can execute system actions.
- Services must be listed in `ALLOWED_SERVICES`.
- Service names are validated before use.
- Commands use `subprocess.run` with argument lists and `shell=False`.
- Dangerous actions require a temporary `/confirm TOKEN`.
- The bot should run as a dedicated non-root Linux user.
- Sudoers should permit only the generated command list.

## Known risks and limitations

- Anyone controlling the authorized Telegram account can trigger allowed administrative actions.
- Telegram bot tokens are bearer secrets. If leaked, rotate the token immediately in BotFather.
- Adding `debianbot` to the Docker group can effectively grant root-equivalent control.
- Allowing restart/stop of critical services can cause outages.
- `apt upgrade -y` can change system state significantly even though it is confirmation-gated.
- This project does not replace host firewalling, SSH hardening, patch management, backups, or monitoring.

## Recommended deployment controls

- Use a dedicated bot token per server.
- Use a private 1:1 chat id where possible.
- Enable 2FA on the Telegram account that controls the bot.
- Keep `ALLOWED_SERVICES` minimal.
- Review `/etc/sudoers.d/debian-telegram-admin-bot` after installation.
- Keep `.env` out of Git and restrict file permissions.
- Periodically review `journalctl` and local bot logs.
- Rotate secrets after any suspected exposure.

## Reporting a vulnerability

Do not open a public GitHub issue for sensitive vulnerabilities.

Preferred process:

1. Create a private security advisory on GitHub if the repository supports it.
2. If private advisories are not enabled, contact the maintainer through the private channel listed in the repository profile.
3. Include reproduction steps, affected version or commit, impact, and suggested fix if available.

Please do not include real Telegram tokens, real chat IDs, public IPs, hostnames, or production logs unless they are redacted.

## Secret handling

Never commit:

- `.env`
- Real Telegram tokens
- Real chat IDs if they identify a private account
- Server hostnames or IP addresses from production
- Logs containing operational details

Use placeholders such as:

```text
TELEGRAM_BOT_TOKEN=REDACTED
AUTHORIZED_CHAT_ID=123456789
```
