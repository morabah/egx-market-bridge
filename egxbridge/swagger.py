from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import requests

@dataclass
class Operation:
    method: str
    path: str
    operation_id: str
    spec: dict[str, Any]

class SwaggerClient:
    def __init__(self, base_url: str, swagger_url: str, timeout: int = 15, token: str = ""):
        self.base_url = base_url.rstrip("/")
        self.swagger_url = swagger_url
        self.timeout = timeout
        self.token = token
        self.session = requests.Session()
        self.spec: dict[str, Any] = {}
        self.operations: list[Operation] = []

    def refresh(self) -> None:
        r = self.session.get(self.swagger_url, timeout=self.timeout)
        r.raise_for_status()
        self.spec = r.json()
        ops: list[Operation] = []
        for path, methods in self.spec.get("paths", {}).items():
            for method, op in methods.items():
                if method.lower() not in {"get", "post", "put", "delete", "patch"}:
                    continue
                ops.append(Operation(method.upper(), path, op.get("operationId", ""), op))
        self.operations = ops

    def find(self, contains: str, method: str | None = None, prefer_prefix: str | None = None) -> Operation | None:
        q = contains.lower()
        candidates = [o for o in self.operations if q in (o.operation_id + " " + o.path).lower()]
        if method:
            candidates = [o for o in candidates if o.method == method.upper()]
        if prefer_prefix:
            preferred = [o for o in candidates if o.path.lower().startswith(prefer_prefix.lower())]
            if preferred:
                candidates = preferred
        return candidates[0] if candidates else None

    @staticmethod
    def parameters(op: Operation) -> list[dict[str, Any]]:
        return list(op.spec.get("parameters", []))

    def call(self, op: Operation, *, query: dict[str, Any] | None = None, body: Any = None) -> Any:
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        url = self.base_url + op.path
        kwargs: dict[str, Any] = {"headers": headers, "timeout": self.timeout}
        if query:
            kwargs["params"] = query
        if body is not None:
            kwargs["json"] = body
        r = self.session.request(op.method, url, **kwargs)
        if r.status_code >= 400:
            snippet = r.text[:500].replace("\n", " ")
            raise RuntimeError(f"{op.method} {op.path} -> HTTP {r.status_code}: {snippet}")
        ctype = r.headers.get("content-type", "")
        if "json" in ctype.lower():
            return r.json()
        try:
            return r.json()
        except Exception:
            return {"text": r.text}
