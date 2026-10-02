from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Protocol

from .types import ToolResult


class Tool(Protocol):
    name: str
    def execute(self, arguments: dict) -> ToolResult: ...
    def verify(self, arguments: dict, result: ToolResult) -> ToolResult: ...


class FileWriteTool:
    name = "file.write"
    def __init__(self, workspace: str | Path) -> None: self.workspace = Path(workspace).resolve()
    def _target(self, value: str) -> Path:
        target = (self.workspace / value).resolve()
        if self.workspace not in target.parents and target != self.workspace: raise ValueError("path escapes workspace")
        return target
    def execute(self, arguments: dict) -> ToolResult:
        try:
            target = self._target(arguments["path"]); content = arguments["content"]
            if not isinstance(content, str): raise ValueError("content must be a string")
            target.parent.mkdir(parents=True, exist_ok=True); target.write_text(content, encoding="utf-8")
            return ToolResult(True, {"path": str(target), "bytes": len(content.encode())})
        except (KeyError, ValueError, OSError) as error: return ToolResult(False, error=str(error))
    def verify(self, arguments: dict, result: ToolResult) -> ToolResult:
        if not result.ok: return result
        try:
            target = self._target(arguments["path"]); expected = arguments["content"]
            actual = target.read_text(encoding="utf-8")
            return ToolResult(actual == expected, result.output, None if actual == expected else "file content mismatch", {"exists": target.exists(), "bytes": target.stat().st_size})
        except OSError as error: return ToolResult(False, result.output, str(error))


class ShellTool:
    name = "shell.run"
    def __init__(self, workspace: str | Path, timeout: int = 30) -> None: self.workspace, self.timeout = str(Path(workspace).resolve()), timeout
    def execute(self, arguments: dict) -> ToolResult:
        command = arguments.get("command")
        if not isinstance(command, list) or not command or not all(isinstance(x, str) for x in command): return ToolResult(False, error="command must be a non-empty argv list")
        try:
            run = subprocess.run(command, cwd=self.workspace, text=True, capture_output=True, timeout=min(int(arguments.get("timeout", self.timeout)), self.timeout), check=False)
            return ToolResult(run.returncode == 0, {"stdout": run.stdout, "stderr": run.stderr, "returncode": run.returncode}, None if run.returncode == 0 else f"exit code {run.returncode}", retryable=False)
        except (OSError, subprocess.TimeoutExpired, ValueError) as error: return ToolResult(False, error=str(error), retryable=isinstance(error, subprocess.TimeoutExpired))
    def verify(self, arguments: dict, result: ToolResult) -> ToolResult: return result
