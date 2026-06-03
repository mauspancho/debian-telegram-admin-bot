from __future__ import annotations

from modules.system import CommandResult, limit_text, run_command


def list_updates(timeout: int, max_chars: int) -> CommandResult:
    update = run_command(
        ["sudo", "/usr/bin/apt", "update"],
        timeout=timeout,
        max_chars=max_chars,
    )
    upgradable = run_command(
        ["sudo", "/usr/bin/apt", "list", "--upgradable"],
        timeout=timeout,
        max_chars=max_chars,
    )
    ok = update.ok and upgradable.ok
    output = f"$ apt update\n{update.output}\n\n$ apt list --upgradable\n{upgradable.output}"
    return CommandResult(ok, limit_text(output, max_chars), upgradable.returncode)


def upgrade(timeout: int, max_chars: int) -> CommandResult:
    return run_command(
        ["sudo", "/usr/bin/apt", "upgrade", "-y"],
        timeout=timeout,
        max_chars=max_chars,
    )
