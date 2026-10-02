"""Planner interfaces and an OpenAI-compatible JSON planner adapter."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol


class PlanValidationError(ValueError):
    pass


def validate_plan(plan: object, allowed_tools: set[str]) -> list[dict]:
    if not isinstance(plan, list) or not plan:
        raise PlanValidationError("plan must be a non-empty list of steps")
    normalized: list[dict] = []
    for index, step in enumerate(plan):
        if not isinstance(step, dict) or set(step) - {"tool", "arguments", "description"}:
            raise PlanValidationError(f"invalid fields in step {index}")
        tool, arguments = step.get("tool"), step.get("arguments")
        if tool not in allowed_tools or not isinstance(arguments, dict):
            raise PlanValidationError(f"invalid tool or arguments in step {index}")
        normalized.append({"tool": tool, "arguments": arguments, "description": str(step.get("description", ""))})
    return normalized


class Planner(Protocol):
    def plan(self, goal: str, context: dict) -> list[dict]: ...


@dataclass(slots=True)
class OpenAICompatiblePlanner:
    """Provider adapter; runtime remains independent of a particular model vendor."""
    endpoint: str
    model: str
    api_key: str
    timeout: int = 45

    @classmethod
    def from_environment(cls) -> "OpenAICompatiblePlanner | None":
        endpoint, model, key = (os.getenv("ELIAN_MODEL_ENDPOINT"), os.getenv("ELIAN_MODEL"), os.getenv("ELIAN_MODEL_API_KEY"))
        return cls(endpoint.rstrip("/"), model, key) if endpoint and model and key else None

    def plan(self, goal: str, context: dict) -> list[dict]:
        prompt = ("Return JSON only: a non-empty list of steps. Each step has tool, arguments, and optional description. "
                  f"Goal: {goal}\nContext: {json.dumps(context, ensure_ascii=False)}")
        request = urllib.request.Request(
            f"{self.endpoint}/chat/completions",
            data=json.dumps({"model": self.model, "messages": [{"role": "user", "content": prompt}], "response_format": {"type": "json_object"}}).encode(),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read())
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as error:
            raise RuntimeError(f"planner request failed: {error}") from error
        content = body["choices"][0]["message"]["content"]
        decoded = json.loads(content)
        return decoded["plan"] if isinstance(decoded, dict) and "plan" in decoded else decoded
