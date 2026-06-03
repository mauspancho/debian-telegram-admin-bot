from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from typing import Callable

from modules.system import CommandResult


ActionCallable = Callable[[], CommandResult]


@dataclass
class PendingAction:
    token: str
    chat_id: int
    description: str
    created_at: float
    expires_at: float
    action: ActionCallable


class ConfirmationManager:
    def __init__(self, ttl_seconds: int) -> None:
        self.ttl_seconds = ttl_seconds
        self._pending: dict[str, PendingAction] = {}

    def create(
        self,
        chat_id: int,
        description: str,
        action: ActionCallable,
    ) -> PendingAction:
        self.cleanup()
        token = secrets.token_hex(4)
        now = time.time()
        pending = PendingAction(
            token=token,
            chat_id=chat_id,
            description=description,
            created_at=now,
            expires_at=now + self.ttl_seconds,
            action=action,
        )
        self._pending[token] = pending
        return pending

    def consume(self, token: str, chat_id: int) -> tuple[bool, str, ActionCallable | None]:
        self.cleanup()
        pending = self._pending.get(token)
        if pending is None:
            return False, "Token invalido o expirado.", None
        if pending.chat_id != chat_id:
            return False, "Este token no pertenece a tu chat_id.", None
        del self._pending[token]
        return True, pending.description, pending.action

    def cleanup(self) -> None:
        now = time.time()
        expired = [
            token for token, pending in self._pending.items() if pending.expires_at <= now
        ]
        for token in expired:
            del self._pending[token]
