# Contributing

Thanks for helping improve Debian Telegram Admin Bot.

This project touches Linux administration and privilege boundaries, so changes should be conservative and easy to audit.

## Ground rules

- Do not add arbitrary command execution.
- Do not introduce `shell=True`.
- Do not broaden sudoers permissions unless there is a clear security review.
- Do not commit real tokens, chat IDs, hostnames, IP addresses, logs, or `.env` files.
- Keep commands explicit and argument-list based.
- Keep user-facing messages in Spanish unless the project decides otherwise.

## Local review checklist

Before opening a pull request:

```bash
python3 -m py_compile bot.py config.py modules/*.py
bash -n install.sh uninstall.sh scripts/*.sh
```

On Debian, also run:

```bash
sudo visudo -c
```

If you changed sudoers generation, test on a disposable Debian VM before proposing the change.

## Pull request checklist

- Explain the motivation and security impact.
- Include manual test steps.
- Update `README.md` if commands, installation, configuration, or behavior changed.
- Update `CHANGELOG.md`.
- Avoid unrelated formatting churn.

## Development setup

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Use fake values in local examples and documentation. Do not run the bot with production credentials from a development checkout.

## Reporting bugs

When filing an issue, include:

- Debian version.
- Python version.
- Install path.
- Service name.
- Sanitized logs.
- Steps to reproduce.

Redact all secrets before posting.
