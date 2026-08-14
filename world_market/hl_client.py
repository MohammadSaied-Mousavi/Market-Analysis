"""
Hyperliquid public-API client for HIP-3 perps.
Single source of truth for all HTTP calls to https://api.hyperliquid.xyz/info.
No auth required. Used by server.py and importable from any script.
"""
from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import requests


class RateLimiter:
    def __init__(self, max_per_sec: float = 8.0):
        self._gap = 1.0 / max_per_sec
        self._lock = threading.Lock()
        self._next_ok = 0.0

    def acquire(self) -> None:
        with self._lock:
            now = time.monotonic()
            wait = self._next_ok - now
            if wait > 0:
                time.sleep(wait)
                now = time.monotonic()
            self._next_ok = now + self._gap


API = "https://api.hyperliquid.xyz/info"
CAP = 5000
FUNDING_INTERVAL_MS = 60 * 60 * 1000

INTERVAL_MS = {
    "1m":  60_000,
    "5m":  5 * 60_000,
    "15m": 15 * 60_000,
    "1h":  60 * 60_000,
    "4h":  4 * 60 * 60_000,
    "1d":  24 * 60 * 60_000,
}

LOOKBACK_MS = {
    "1d":   1 * 86_400_000,
    "7d":   7 * 86_400_000,
    "30d":  30 * 86_400_000,
    "90d":  90 * 86_400_000,
    "180d": 180 * 86_400_000,
    "1y":   365 * 86_400_000,
    "all":  5 * 365 * 86_400_000,
}


@dataclass
class HLClient:
    dex: str = "xyz"
    timeout: int = 30
    max_retries: int = 6
    max_per_sec: float = 8.0
    session: requests.Session = field(default_factory=requests.Session)
    rate: RateLimiter = field(init=False)

    def __post_init__(self):
        self.rate = RateLimiter(self.max_per_sec)

    def post(self, body: dict) -> Any:
        last_exc = None
        for attempt in range(self.max_retries):
            self.rate.acquire()
            try:
                r = self.session.post(API, json=body, timeout=self.timeout)
                if r.status_code == 429:
                    ra = r.headers.get("Retry-After")
                    wait = float(ra) if (ra and ra.replace(".", "", 1).isdigit()) else (2.0 * (2 ** attempt))
                    time.sleep(min(wait, 30.0))
                    last_exc = RuntimeError(f"429 rate limited (attempt {attempt+1})")
                    continue
                r.raise_for_status()
                return r.json()
            except requests.HTTPError as e:
                last_exc = e
                time.sleep(0.5 * (2 ** attempt))
            except Exception as e:
                last_exc = e
                time.sleep(0.5 * (2 ** attempt))
        raise RuntimeError(f"hyperliquid call failed: {body.get('type')}: {last_exc}")

    def list_dexes(self) -> list[dict | None]:
        return self.post({"type": "perpDexs"})

    def meta(self, dex: str | None = None) -> dict:
        d = dex if dex is not None else self.dex
        return self.post({"type": "meta", "dex": d})

    def universe(self, dex: str | None = None) -> list[str]:
        m = self.meta(dex)
        return [u.get("name") for u in m.get("universe", []) if u.get("name")]

    def asset_ctxs(self, dex: str | None = None) -> tuple[dict, list[dict]]:
        d = dex if dex is not None else self.dex
        resp = self.post({"type": "metaAndAssetCtxs", "dex": d})
        if isinstance(resp, list) and len(resp) == 2:
            return resp[0], resp[1]
        raise RuntimeError(f"unexpected metaAndAssetCtxs shape: {type(resp)}")

    def snapshot(self, dex: str | None = None) -> list[dict]:
        meta, ctxs = self.asset_ctxs(dex)
        names = [u.get("name") for u in meta.get("universe", [])]
        out = []
        for name, ctx in zip(names, ctxs):
            if not name or not isinstance(ctx, dict):
                continue
            out.append({
                "coin": name,
                "fundingRate": _f(ctx.get("funding")),
                "mark":        _f(ctx.get("markPx")),
                "oracle":      _f(ctx.get("oraclePx")),
                "mid":         _f(ctx.get("midPx")),
                "premium":     _f(ctx.get("premium")),
                "openInterest":_f(ctx.get("openInterest")),
                "dayNtlVlm":   _f(ctx.get("dayNtlVlm")),
                "prevDayPx":   _f(ctx.get("prevDayPx")),
            })
        return out

    def fetch_candles(self, coin: str, interval: str, start_ms: int, end_ms: int) -> list[dict]:
        step = INTERVAL_MS[interval]
        chunk = CAP * step
        out: list[dict] = []
        seen: set[int] = set()
        cur = start_ms
        while cur < end_ms:
            chunk_end = min(cur + chunk, end_ms)
            rows = self.post({
                "type": "candleSnapshot",
                "req": {"coin": coin, "interval": interval, "startTime": cur, "endTime": chunk_end},
            }) or []
            for r in rows:
                t = r.get("t")
                if t is None or t in seen:
                    continue
                seen.add(t); out.append(r)
            if not rows:
                cur = chunk_end
            else:
                last = max(r["t"] for r in rows)
                cur = max(last + step, cur + step)
        out.sort(key=lambda r: r["t"])
        return out

    def fetch_funding(self, coin: str, start_ms: int, end_ms: int) -> list[dict]:
        chunk = CAP * FUNDING_INTERVAL_MS
        out: list[dict] = []
        seen: set[int] = set()
        cur = start_ms
        while cur < end_ms:
            chunk_end = min(cur + chunk, end_ms)
            rows = self.post({
                "type": "fundingHistory", "coin": coin,
                "startTime": cur, "endTime": chunk_end,
            }) or []
            for r in rows:
                t = r.get("time")
                if t is None or t in seen:
                    continue
                seen.add(t); out.append(r)
            if not rows:
                cur = chunk_end
            else:
                last = max(r["time"] for r in rows)
                cur = max(last + FUNDING_INTERVAL_MS, cur + FUNDING_INTERVAL_MS)
        out.sort(key=lambda r: r["time"])
        return out

    def fetch_bundle(self, coin: str, interval: str, lookback: str) -> dict:
        end_ms = int(time.time() * 1000)
        start_ms = end_ms - LOOKBACK_MS[lookback]
        candles = self.fetch_candles(coin, interval, start_ms, end_ms)
        funding = self.fetch_funding(coin, start_ms, end_ms)
        return {
            "coin": coin, "dex": self.dex,
            "interval": interval, "lookback": lookback,
            "start_ms": start_ms, "end_ms": end_ms,
            "fetched_at": end_ms,
            "fetched_at_iso": datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc).isoformat(),
            "candles": candles, "funding": funding,
        }

    def fetch_many(
        self,
        coins: list[str],
        interval: str,
        lookback: str,
        workers: int = 8,
        on_progress=None,
    ) -> dict[str, dict]:
        out: dict[str, dict] = {}
        done = 0
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(self.fetch_bundle, c, interval, lookback): c for c in coins}
            for fut in as_completed(futs):
                coin = futs[fut]
                try:
                    out[coin] = fut.result()
                except Exception as e:
                    out[coin] = {"error": str(e), "coin": coin}
                done += 1
                if on_progress:
                    on_progress(done, len(coins), coin)
        return out


def _f(v) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None