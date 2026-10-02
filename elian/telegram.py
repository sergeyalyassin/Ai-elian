"""Transport-neutral Telegram control-plane command translation.

A bot adapter supplies updates and sends the returned dictionaries; this module performs
no network I/O and therefore never stores Telegram credentials.
"""
from __future__ import annotations

from .runtime import ElianRuntime


class TelegramControlPlane:
    def __init__(self, runtime: ElianRuntime) -> None:
        self.runtime = runtime

    def handle(self, user_id: str, chat_id: str, text: str) -> dict:
        command = text.strip().split(maxsplit=1)[0].lower()
        if command == "/status": return self.runtime.handle_message(user_id, chat_id, "status")
        if command == "/cancel": return self.runtime.handle_message(user_id, chat_id, "cancel")
        if command == "/resume": return self.runtime.handle_message(user_id, chat_id, "resume")
        if command == "/tools": return {"kind": "tools", "tools": sorted(self.runtime.orchestrator.tool_names)}
        if command == "/queue": return {"kind": "queue", "recoverable": [task.dump() for task in self.runtime.store.recoverable_tasks()]}
        return self.runtime.handle_message(user_id, chat_id, text)
