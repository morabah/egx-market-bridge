from __future__ import annotations
from typing import Any
from datetime import datetime, timezone
import re


def nk(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def unwrap_rows(obj: Any) -> list[dict[str, Any]]:
    if obj is None:
        return []
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict)]
    if isinstance(obj, dict):
        # Common API wrappers first.
        for k in ("data", "result", "results", "items", "rows", "value", "marketWatch", "marketwatch", "trades", "chartData", "graphData"):
            v = obj.get(k)
            if isinstance(v, list):
                return [x for x in v if isinstance(x, dict)]
            if isinstance(v, dict):
                rr = unwrap_rows(v)
                if rr:
                    return rr
        # Search any list field.
        for v in obj.values():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                return [x for x in v if isinstance(x, dict)]
        return [obj]
    return []


def flat(d: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in d.items():
        key = f"{prefix}.{k}" if prefix else str(k)
        if isinstance(v, dict):
            out.update(flat(v, key))
        else:
            out[key] = v
    return out


def pick(d: dict[str, Any], candidates: list[str], default=None):
    fd = flat(d)
    normalized = {nk(k): v for k, v in fd.items()}
    for c in candidates:
        nc = nk(c)
        if nc in normalized and normalized[nc] not in (None, ""):
            return normalized[nc]
    # suffix match helps nested wrappers.
    for c in candidates:
        nc = nk(c)
        for k, v in normalized.items():
            if k.endswith(nc) and v not in (None, ""):
                return v
    return default


def num(v):
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace(",", "").replace("%", "").strip()
    try:
        return float(s)
    except Exception:
        return None


def sym_of(d: dict[str, Any]) -> str:
    return str(pick(d, ["symbol", "ticker", "symbolCode", "shortName", "code", "symbolName"], "")).upper().strip()


def normalize_quote(raw: Any, symbol: str = "") -> dict[str, Any]:
    rows = unwrap_rows(raw)
    row = rows[0] if rows else {}
    if symbol and len(rows) > 1:
        for r in rows:
            s = sym_of(r)
            if s == symbol.upper() or s.startswith(symbol.upper()):
                row = r; break
    return {
        "symbol": symbol.upper() or sym_of(row),
        "timestamp": pick(row, ["timestamp", "time", "lastUpdate", "updateTime", "tradeTime", "dateTime"]),
        "last": num(pick(row, ["lastPrice", "last", "closePrice", "price", "tradePrice", "close"])),
        "open": num(pick(row, ["openPrice", "open"])),
        "high": num(pick(row, ["highPrice", "high"])),
        "low": num(pick(row, ["lowPrice", "low"])),
        "prev_close": num(pick(row, ["previousClose", "prevClose", "previousPrice", "closeYesterday"])),
        "change_pct": num(pick(row, ["changePercent", "changePct", "percentChange", "changePercentage"])),
        "volume": num(pick(row, ["volume", "totalVolume", "tradedVolume", "quantity", "totalQuantity"])),
        "turnover": num(pick(row, ["turnover", "value", "totalValue", "tradedValue"])),
        "trades": num(pick(row, ["trades", "tradeCount", "numberOfTrades", "noOfTrades", "transactions"])),
        "bid": num(pick(row, ["bestBid", "bidPrice", "bid"])),
        "bid_qty": num(pick(row, ["bestBidQty", "bidQuantity", "bidQty", "bidVolume"])),
        "ask": num(pick(row, ["bestAsk", "askPrice", "offerPrice", "ask", "offer"])),
        "ask_qty": num(pick(row, ["bestAskQty", "askQuantity", "askQty", "offerQty", "askVolume"])),
        "captured_at_utc": datetime.now(timezone.utc).isoformat()
    }


def normalize_depth(raw: Any, symbol: str = "") -> list[dict[str, Any]]:
    rows = unwrap_rows(raw)
    out: list[dict[str, Any]] = []
    for r in rows:
        # Row may contain both bid and ask columns.
        bp = num(pick(r, ["bidPrice", "buyPrice", "bestBid", "bid"])); bq = num(pick(r, ["bidQty", "bidQuantity", "buyQty", "buyQuantity", "bidVolume"]));
        ap = num(pick(r, ["askPrice", "offerPrice", "sellPrice", "bestAsk", "ask", "offer"])); aq = num(pick(r, ["askQty", "askQuantity", "offerQty", "sellQty", "sellQuantity", "askVolume"]));
        if bp is not None:
            out.append({"symbol": symbol.upper(), "side": "BID", "price": bp, "qty": bq, "orders": num(pick(r,["bidOrders","buyOrders","bidCount"])), "raw": r})
        if ap is not None:
            out.append({"symbol": symbol.upper(), "side": "ASK", "price": ap, "qty": aq, "orders": num(pick(r,["askOrders","sellOrders","offerOrders","askCount"])), "raw": r})
        if bp is None and ap is None:
            side = str(pick(r, ["side", "buySell", "orderSide", "type"], "")).upper()
            price = num(pick(r, ["price", "levelPrice"])); qty = num(pick(r, ["qty", "quantity", "volume", "size"]));
            if price is not None and side:
                if side in {"B", "BUY", "BID", "1"}: side = "BID"
                elif side in {"S", "SELL", "ASK", "OFFER", "2"}: side = "ASK"
                out.append({"symbol": symbol.upper(), "side": side, "price": price, "qty": qty, "orders": num(pick(r,["orders","orderCount","count"])), "raw": r})
    out.sort(key=lambda x: (0 if x["side"] == "BID" else 1, -(x["price"] or 0) if x["side"] == "BID" else (x["price"] or 0)))
    return out


def normalize_trades(raw: Any, symbol: str = "") -> list[dict[str, Any]]:
    rows = unwrap_rows(raw)
    out = []
    for r in rows:
        p = num(pick(r, ["tradePrice", "price", "lastPrice"])); q = num(pick(r, ["tradeQty", "qty", "quantity", "volume", "size"]));
        if p is None:
            continue
        out.append({
            "symbol": symbol.upper() or sym_of(r),
            "time": pick(r, ["tradeTime", "time", "timestamp", "dateTime", "executionTime"]),
            "price": p,
            "qty": q,
            "value": num(pick(r, ["tradeValue", "value", "turnover"])),
            "raw": r
        })
    return out


def normalize_candles(raw: Any, symbol: str = "") -> list[dict[str, Any]]:
    rows = unwrap_rows(raw)
    out = []
    for r in rows:
        o = num(pick(r, ["open", "openPrice"])); h = num(pick(r, ["high", "highPrice"])); l = num(pick(r, ["low", "lowPrice"])); c = num(pick(r, ["close", "closePrice", "lastPrice"]));
        if all(x is None for x in (o,h,l,c)):
            continue
        out.append({
            "symbol": symbol.upper() or sym_of(r),
            "time": pick(r, ["time", "timestamp", "date", "dateTime", "period"]),
            "open": o, "high": h, "low": l, "close": c,
            "volume": num(pick(r, ["volume", "totalVolume", "qty", "quantity"])),
            "raw": r
        })
    return out
