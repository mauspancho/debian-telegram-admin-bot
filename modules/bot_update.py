from __future__ import annotations

from pathlib import Path

from modules.system import CommandResult, limit_text, run_command

BOT_VERSION = "0.2.0"


def resolve_repo_path(install_path: Path, bot_repo_path: Path | None) -> Path | None:
    candidates = [bot_repo_path, install_path]
    for candidate in candidates:
        if candidate and (candidate / ".git").exists():
            return candidate
    return None


def version(max_chars: int) -> CommandResult:
    return CommandResult(True, limit_text(f"Debian Telegram Admin Bot {BOT_VERSION}", max_chars))


def update_check(
    install_path: Path,
    bot_repo_path: Path | None,
    timeout: int,
    max_chars: int,
) -> CommandResult:
    repo = resolve_repo_path(install_path, bot_repo_path)
    if repo is None:
        return CommandResult(False, "No hay repositorio .git. Define BOT_REPO_PATH si aplica.")
    fetch = run_command(["/usr/bin/git", "-C", str(repo), "fetch", "--dry-run"], timeout, max_chars)
    status = run_command(["/usr/bin/git", "-C", str(repo), "status", "-sb"], timeout, max_chars)
    return CommandResult(
        fetch.ok and status.ok,
        limit_text(f"$ git fetch --dry-run\n{fetch.output}\n\n$ git status -sb\n{status.output}", max_chars),
    )


def update_bot(
    install_path: Path,
    bot_repo_path: Path | None,
    timeout: int,
    max_chars: int,
) -> CommandResult:
    repo = resolve_repo_path(install_path, bot_repo_path)
    if repo is None:
        return CommandResult(False, "No hay repositorio .git. Define BOT_REPO_PATH si aplica.")
    return run_command(
        ["/usr/bin/git", "-C", str(repo), "pull", "--ff-only"],
        timeout=timeout,
        max_chars=max_chars,
    )
