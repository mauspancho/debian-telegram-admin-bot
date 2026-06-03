from __future__ import annotations

import socket
import subprocess
from dataclasses import dataclass
from pathlib import Path
from shutil import which


@dataclass(frozen=True)
class CommandResult:
    ok: bool
    output: str
    returncode: int | None = None


def limit_text(text: str, max_chars: int = 3500) -> str:
    clean = text.strip()
    if len(clean) <= max_chars:
        return clean or "(sin salida)"
    suffix = "\n\n[Salida recortada por seguridad]"
    return clean[: max_chars - len(suffix)] + suffix


def run_command(
    args: list[str],
    timeout: int = 30,
    max_chars: int = 3500,
) -> CommandResult:
    try:
        completed = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
            check=False,
        )
    except FileNotFoundError:
        return CommandResult(False, f"Comando no encontrado: {args[0]}", None)
    except subprocess.TimeoutExpired:
        return CommandResult(False, f"Comando excedio el timeout de {timeout}s", None)

    output = "\n".join(
        part for part in [completed.stdout.strip(), completed.stderr.strip()] if part
    )
    return CommandResult(
        completed.returncode == 0,
        limit_text(output, max_chars),
        completed.returncode,
    )


def command_exists(command: str) -> bool:
    return which(command) is not None


def hostname() -> str:
    return socket.gethostname()


def status(timeout: int, max_chars: int) -> CommandResult:
    host_cmd = which("hostname") or "/usr/bin/hostname"
    uname_cmd = which("uname") or "/usr/bin/uname"
    uptime_cmd = which("uptime") or "/usr/bin/uptime"
    host_result = run_command([host_cmd], timeout=timeout, max_chars=max_chars)
    kernel_result = run_command([uname_cmd, "-r"], timeout=timeout, max_chars=max_chars)
    uptime_result = run_command([uptime_cmd, "-p"], timeout=timeout, max_chars=max_chars)
    try:
        loadavg = Path("/proc/loadavg").read_text(encoding="utf-8").strip()
    except OSError:
        loadavg = "no disponible"

    output = "\n".join(
        [
            f"Hostname: {host_result.output}",
            f"Kernel: {kernel_result.output}",
            f"Uptime: {uptime_result.output}",
            f"Carga: {loadavg}",
        ]
    )
    return CommandResult(
        host_result.ok and kernel_result.ok and uptime_result.ok,
        limit_text(output, max_chars),
    )


def ram(timeout: int, max_chars: int) -> CommandResult:
    return run_command(["/usr/bin/free", "-h"], timeout=timeout, max_chars=max_chars)


def disk(timeout: int, max_chars: int) -> CommandResult:
    return run_command(
        ["/usr/bin/df", "-h", "-x", "tmpfs", "-x", "devtmpfs"],
        timeout=timeout,
        max_chars=max_chars,
    )


def local_ip(timeout: int, max_chars: int) -> CommandResult:
    ip_cmd = which("ip") or "/usr/sbin/ip"
    ip_result = run_command(
        [ip_cmd, "-o", "-4", "addr", "show", "scope", "global"],
        timeout=timeout,
        max_chars=max_chars,
    )
    if ip_result.ok and ip_result.output != "(sin salida)":
        lines = []
        for raw in ip_result.output.splitlines():
            parts = raw.split()
            if len(parts) >= 4:
                lines.append(f"{parts[1]}: {parts[3]}")
        if lines:
            return CommandResult(True, "IPv4 locales:\n" + "\n".join(lines))

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(2)
            sock.connect(("1.1.1.1", 80))
            return CommandResult(True, f"IP local principal: {sock.getsockname()[0]}")
    except OSError as exc:
        return CommandResult(False, f"No se pudo obtener la IP local: {exc}")


def processes(timeout: int, max_chars: int) -> CommandResult:
    return run_command(
        [
            "/bin/ps",
            "-eo",
            "pid,user,pcpu,pmem,comm",
            "--sort=-pcpu",
        ],
        timeout=timeout,
        max_chars=max_chars,
    )
