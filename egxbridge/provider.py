from __future__ import annotations

from typing import Any
from datetime import datetime, timedelta
import json

from .swagger import SwaggerClient, Operation

class EGIDProvider:
    """Swagger-driven EGID client.

    It deliberately discovers parameters at runtime instead of hardcoding undocumented
    query names. This makes the tool resilient if EGID renames symbol parameters.
    """
    def __init__(self, base_url: str, swagger_url: str, timeout: int = 15, mode: str = "delayed", token: str = ""):
        self.mode = mode.lower().strip()
        self.prefix = "/api/DelayedFeed" if self.mode != "feed" else "/api/Feed"
        self.client = SwaggerClient(base_url, swagger_url, timeout=timeout, token=token)
        self.client.refresh()

    def _find(self, name: str, method: str | None = None) -> Operation:
        op = self.client.find(name, method=method, prefer_prefix=self.prefix)
        if not op:
            raise RuntimeError(f"Could not discover EGID operation containing '{name}' under {self.prefix}.")
        return op

    @staticmethod
    def _guess_param_value(name: str, symbol: str = ""):
        n = name.lower()
        if any(x in n for x in ("symbol", "ticker", "code")):
            return symbol
        if "market" in n:
            return "EGX"
        if any(x in n for x in ("lang", "language")):
            return "en"
        if any(x in n for x in ("count", "top", "limit", "rows")):
            return 100
        if "from" in n and "date" in n:
            return (datetime.now() - timedelta(days=45)).strftime("%Y-%m-%d")
        if "to" in n and "date" in n:
            return datetime.now().strftime("%Y-%m-%d")
        if n in {"date", "tradingdate"}:
            return datetime.now().strftime("%Y-%m-%d")
        return None

    def _query_for(self, op: Operation, symbol: str = "") -> dict[str, Any]:
        q: dict[str, Any] = {}
        unknown_required = []
        for p in op.spec.get("parameters", []):
            if p.get("in") != "query":
                continue
            name = p.get("name", "")
            val = self._guess_param_value(name, symbol)
            if val not in (None, ""):
                q[name] = val
            elif p.get("required"):
                unknown_required.append(name)
        if unknown_required:
            raise RuntimeError(f"Endpoint {op.path} needs unknown required query parameters: {unknown_required}. Use probe.py to inspect Swagger.")
        return q

    def _resolve_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        if "$ref" in schema:
            name = schema["$ref"].split("/")[-1]
            return self.client.spec.get("components", {}).get("schemas", {}).get(name, {})
        return schema

    def _body_for(self, op: Operation, symbol: str = "") -> dict[str, Any]:
        rb = op.spec.get("requestBody", {})
        content = rb.get("content", {})
        js = content.get("application/json", {})
        schema = self._resolve_schema(js.get("schema", {}))
        props = schema.get("properties", {})
        req = set(schema.get("required", []))
        body: dict[str, Any] = {}
        for name, ps in props.items():
            v = self._guess_param_value(name, symbol)
            if v is None:
                nl = name.lower()
                if "period" in nl or "interval" in nl:
                    # Let server default if optional. Use Daily-ish numeric enum only when required.
                    if name in req:
                        v = 0
            if v is not None:
                body[name] = v
        return body

    def call_named(self, name: str, symbol: str = "", method: str | None = None) -> Any:
        op = self._find(name, method=method)
        query = self._query_for(op, symbol)
        body = self._body_for(op, symbol) if op.method in {"POST", "PUT", "PATCH"} else None
        return self.client.call(op, query=query, body=body)

    def market_watch(self):
        for name in ("getAllMarketWatch", "GetEGXMarketWatch", "GetTodayMarketWatch"):
            try:
                return self.call_named(name)
            except Exception:
                pass
        raise RuntimeError("No market-watch endpoint succeeded.")

    def quote(self, symbol: str):
        return self.call_named("getMarketWatchForSymbol", symbol)

    def depth(self, symbol: str):
        return self.call_named("getMarketDepth", symbol)

    def trades(self, symbol: str):
        for name in ("getTodaySymbolTrades", "getSymbolTrades"):
            try:
                return self.call_named(name, symbol)
            except Exception:
                pass
        raise RuntimeError(f"No trades endpoint succeeded for {symbol}.")

    def chart(self, symbol: str):
        for name in ("getSymbolGraphData", "GetSymbolChart", "getSymbolHistory"):
            try:
                return self.call_named(name, symbol)
            except Exception:
                pass
        raise RuntimeError(f"No chart/history endpoint succeeded for {symbol}.")

    def probe(self, symbol: str) -> list[dict[str, Any]]:
        tests = [
            "getMarketWatchForSymbol", "getMarketDepth", "getMarketDepthPerPrice",
            "getTodaySymbolTrades", "getSymbolTrades", "getSymbolGraphData",
            "getAllMarketWatch", "getMarketSummary", "getMarketStatus"
        ]
        out = []
        for name in tests:
            try:
                op = self._find(name)
                q = self._query_for(op, symbol)
                body = self._body_for(op, symbol) if op.method == "POST" else None
                data = self.client.call(op, query=q, body=body)
                preview = json.dumps(data, ensure_ascii=False)[:1000]
                out.append({"name": name, "ok": True, "method": op.method, "path": op.path, "query": q, "preview": preview})
            except Exception as e:
                out.append({"name": name, "ok": False, "error": str(e)})
        return out
