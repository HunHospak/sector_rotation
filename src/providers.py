"""Data providers for sector_rotation — isolated so they can be swapped/mocked."""
from __future__ import annotations

import yfinance as yf


def get_window_returns(tickers: list[str], window_short: int, window_long: int) -> dict:
    """Percent returns over the short and long windows for each ticker.

    Returns { ticker: {"ret_short": float, "ret_long": float, "vol_ratio": float|None} }.
    vol_ratio = recent short-window avg volume / long-window avg volume (a soft flow proxy).
    """
    if not tickers:
        return {}
    lookback = max(window_long + 5, 30)
    data = yf.download(
        tickers, period=f"{lookback}d", interval="1d", group_by="ticker",
        auto_adjust=True, threads=True, progress=False,
    )
    out: dict[str, dict] = {}
    multi = len(tickers) > 1
    for t in tickers:
        try:
            df = data[t] if multi else data
            closes = df["Close"].dropna()
            if len(closes) < window_long + 1:
                continue
            last = float(closes.iloc[-1])
            ref_s = float(closes.iloc[-1 - window_short])
            ref_l = float(closes.iloc[-1 - window_long])
            rec = {
                "ret_short": (last - ref_s) / ref_s * 100.0 if ref_s else 0.0,
                "ret_long": (last - ref_l) / ref_l * 100.0 if ref_l else 0.0,
                "vol_ratio": None,
            }
            try:
                vols = df["Volume"].dropna()
                if len(vols) >= window_long:
                    vs = float(vols.iloc[-window_short:].mean())
                    vl = float(vols.iloc[-window_long:].mean())
                    if vl > 0:
                        rec["vol_ratio"] = round(vs / vl, 3)
            except Exception:
                pass
            out[t] = rec
        except Exception:
            continue
    return out
