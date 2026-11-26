"""Data providers for sector_rotation — isolated so they can be swapped/mocked."""
from __future__ import annotations

import logging
import math

import pandas as pd
import yfinance as yf


def get_window_returns(tickers: list[str], window_short: int, window_long: int) -> dict:
    """Percent returns over the short and long windows for each ticker.

    Returns per-ticker returns with the observation dates used for both windows.
    vol_ratio = recent short-window avg volume / long-window avg volume (a soft flow proxy).
    """
    if not tickers:
        return {}
    max_window = max(window_short, window_long)
    lookback = max(2 * max_window, 30)
    try:
        data = yf.download(
            tickers, period=f"{lookback}d", interval="1d", group_by="ticker",
            auto_adjust=True, threads=True, progress=False,
        )
    except Exception as exc:
        logging.getLogger(__name__).warning("Price download failed (%s)", type(exc).__name__)
        return {}
    if data is None or data.empty:
        return {}
    out: dict[str, dict] = {}
    grouped = isinstance(data.columns, pd.MultiIndex)
    if not grouped and len(tickers) != 1:
        return {}
    for t in tickers:
        try:
            df = (data[t] if grouped else data).sort_index()
            if not isinstance(df.index, pd.DatetimeIndex):
                continue
            df = df.loc[df.index.notna() & ~df.index.duplicated(keep="last")]
            closes = df["Close"].dropna()
            if len(closes) < max_window + 1:
                continue
            last = float(closes.iloc[-1])
            ref_s = float(closes.iloc[-1 - window_short])
            ref_l = float(closes.iloc[-1 - window_long])
            if not all(math.isfinite(price) and price > 0 for price in (last, ref_s, ref_l)):
                continue
            rec = {
                "ret_short": (last - ref_s) / ref_s * 100.0,
                "ret_long": (last - ref_l) / ref_l * 100.0,
                "vol_ratio": None,
                "as_of": closes.index[-1].date().isoformat(),
                "short_start": closes.index[-1 - window_short].date().isoformat(),
                "long_start": closes.index[-1 - window_long].date().isoformat(),
            }
            try:
                vols = df.loc[closes.index, "Volume"].dropna()
                if len(vols) >= max_window:
                    vs = float(vols.iloc[-window_short:].mean())
                    vl = float(vols.iloc[-window_long:].mean())
                    if math.isfinite(vs) and math.isfinite(vl) and vl > 0:
                        rec["vol_ratio"] = round(vs / vl, 3)
            except Exception:
                pass
            out[t] = rec
        except Exception:
            continue
    return out
