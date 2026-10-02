"""Stateful browser tool with action → observation → verification semantics.

The concrete Playwright backend is intentionally loaded only when a browser task runs,
so the durable runtime and non-browser deployments have no mandatory browser dependency.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from .types import ToolResult


class BrowserBackend(Protocol):
    def navigate(self, url: str) -> None: ...
    def click(self, selector: str) -> None: ...
    def fill(self, selector: str, value: str) -> None: ...
    def press(self, key: str) -> None: ...
    def type(self, selector: str, value: str) -> None: ...
    def wait_for(self, selector: str) -> None: ...
    def upload(self, selector: str, path: str) -> None: ...
    def new_tab(self, url: str | None = None) -> None: ...
    def select_tab(self, index: int) -> None: ...
    def cookies(self) -> list[dict]: ...
    def save_auth(self, path: str) -> None: ...
    def content(self) -> str: ...
    def url(self) -> str: ...
    def screenshot(self, path: str) -> None: ...


@dataclass(slots=True)
class BrowserState:
    url: str = ""
    observation: dict[str, Any] = field(default_factory=dict)


class BrowserTool:
    name = "browser.action"
    def __init__(self, backend: BrowserBackend, artifacts: str | Path = "data/browser") -> None:
        self.backend, self.state = backend, BrowserState()
        self.artifacts = Path(artifacts); self.artifacts.mkdir(parents=True, exist_ok=True)

    def execute(self, arguments: dict) -> ToolResult:
        action = arguments.get("action")
        try:
            if action == "navigate": self.backend.navigate(str(arguments["url"]))
            elif action == "click": self.backend.click(str(arguments["selector"]))
            elif action == "fill": self.backend.fill(str(arguments["selector"]), str(arguments["value"]))
            elif action == "press": self.backend.press(str(arguments["key"]))
            elif action == "type": self.backend.type(str(arguments["selector"]), str(arguments["value"]))
            elif action == "wait_for": self.backend.wait_for(str(arguments["selector"]))
            elif action == "upload": self.backend.upload(str(arguments["selector"]), str(arguments["path"]))
            elif action == "new_tab": self.backend.new_tab(arguments.get("url"))
            elif action == "select_tab": self.backend.select_tab(int(arguments["index"]))
            elif action == "cookies": return ToolResult(True, self.backend.cookies(), evidence={"observed": True})
            elif action == "save_auth": self.backend.save_auth(str(self.artifacts / str(arguments.get("name", "auth.json"))))
            elif action == "screenshot": self.backend.screenshot(str(self.artifacts / str(arguments.get("name", "page.png"))))
            elif action != "observe": return ToolResult(False, error=f"unsupported browser action: {action}")
            self.state.url = self.backend.url()
            self.state.observation = {"url": self.state.url, "content": self.backend.content()[:20_000]}
            return ToolResult(True, dict(self.state.observation), evidence={"observed": True})
        except (KeyError, OSError, ValueError, RuntimeError) as error:
            return ToolResult(False, error=str(error), retryable=action in {"navigate", "click"})

    def verify(self, arguments: dict, result: ToolResult) -> ToolResult:
        if not result.ok: return result
        expected_url, contains = arguments.get("expect_url"), arguments.get("expect_text")
        url_ok = not expected_url or self.state.url.startswith(str(expected_url))
        text_ok = not contains or str(contains) in self.state.observation.get("content", "")
        return ToolResult(url_ok and text_ok, result.output, None if url_ok and text_ok else "browser postcondition failed", {**result.evidence, "url_ok": url_ok, "text_ok": text_ok})
