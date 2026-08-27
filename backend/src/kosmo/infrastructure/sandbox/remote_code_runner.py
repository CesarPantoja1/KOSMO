from __future__ import annotations

import base64
import io
import tarfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import httpx

from kosmo.contracts.sdd.codegen import ValidationRunResult, ValidationStep, ValidationStepResult
from kosmo.domain.codegen.parse_validation_output import parse_step_output


class RemoteCodeRunnerError(RuntimeError):
    """The isolated runner could not accept or execute a validation request."""


class RemoteCodeRunner:
    """Runs generated code in a separate container using an archive, never the shared volume."""

    def __init__(self, base_url: str, token: str, *, client: httpx.AsyncClient | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._client = client or httpx.AsyncClient(base_url=self._base_url, timeout=httpx.Timeout(900, connect=10))
        self._owns_client = client is None

    @staticmethod
    def _archive_workspace(workspace_dir: str) -> str:
        root = Path(workspace_dir).resolve()
        if not root.is_dir():
            raise RemoteCodeRunnerError(f"Workspace does not exist: {workspace_dir}")
        output = io.BytesIO()
        ignored = {"node_modules", ".git", ".next", ".turbo", "coverage"}
        with tarfile.open(fileobj=output, mode="w:gz") as archive:
            for path in root.rglob("*"):
                relative = path.relative_to(root)
                if any(part in ignored for part in relative.parts):
                    continue
                if path.is_file() and not path.is_symlink():
                    archive.add(path, arcname=str(relative).replace("\\", "/"), recursive=False)
        return base64.b64encode(output.getvalue()).decode("ascii")

    async def _run(self, workspace_dir: str, payload: dict[str, object]) -> dict[str, Any]:
        payload["archive"] = self._archive_workspace(workspace_dir)
        response = await self._client.post("/run", json=payload, headers={"Authorization": f"Bearer {self._token}"})
        if not response.is_success:
            raise RemoteCodeRunnerError(f"Runner returned HTTP {response.status_code}: {response.text[:500]}")
        data = response.json()
        if not isinstance(data, dict):
            raise RemoteCodeRunnerError("Runner returned an invalid response")
        return cast(dict[str, Any], data)

    @staticmethod
    def _result(raw: dict[str, Any], step: ValidationStep) -> ValidationStepResult:
        output = str(raw.get("output", ""))
        exit_code = int(raw.get("exit_code", 1))
        duration_ms = int(raw.get("duration_ms", 0))
        return parse_step_output(step, output, exit_code, duration_ms)

    async def run_step(
        self, workspace_dir: str, step: ValidationStep, *, timeout_seconds: int = 300
    ) -> ValidationStepResult:
        data = await self._run(
            workspace_dir, {"operation": "step", "step": str(step), "timeout_seconds": timeout_seconds}
        )
        return self._result(cast(dict[str, Any], data["result"]), step)

    async def run_command(
        self, workspace_dir: str, command: str, *, timeout_seconds: int = 300
    ) -> ValidationStepResult:
        data = await self._run(
            workspace_dir, {"operation": "command", "command": command, "timeout_seconds": timeout_seconds}
        )
        return self._result(cast(dict[str, Any], data["result"]), ValidationStep.TESTS)

    async def run_pipeline(
        self,
        workspace_dir: str,
        steps: tuple[ValidationStep, ...] = (
            ValidationStep.TYPECHECK,
            ValidationStep.LINT,
            ValidationStep.TESTS,
            ValidationStep.BUILD,
        ),
        run_id: str = "",
    ) -> ValidationRunResult:
        data = await self._run(
            workspace_dir, {"operation": "pipeline", "steps": [str(step) for step in steps], "run_id": run_id}
        )
        results = tuple(
            self._result(item, ValidationStep(str(item["step"])))
            for item in cast(list[dict[str, Any]], data.get("results", []))
        )
        errors = tuple(str(error) for error in cast(list[object], data.get("error_summary", [])))
        return ValidationRunResult(
            steps=results,
            all_passed=bool(data.get("all_passed")),
            total_duration_ms=sum(result.duration_ms for result in results),
            executed_at=datetime.now(UTC),
            error_summary=errors,
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
