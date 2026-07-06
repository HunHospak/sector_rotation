"""Pure logic — no I/O, easy to unit-test.

Relative-strength based sector rotation. This is NOT true institutional flow data
(that needs 13F / dark-pool feeds); it is a transparent proxy: how each sector ETF is
performing versus the benchmark on a short and long window, blended into a flow score.
"""
from __future__ import annotations


def analyze(returns: dict, sector_names: dict, benchmark: str, thr: float) -> dict:
    """Build the rotation table.

    returns: { ticker: {"ret_short","ret_long","vol_ratio"} } incl. the benchmark.
    Returns {"benchmark", "sectors":[...], "rotating_in":[...], "rotating_out":[...]}.
    """
    bench = returns.get(benchmark)
    if not bench:
        return {"benchmark": benchmark, "sectors": [], "rotating_in": [], "rotating_out": []}

    rows = []
    for etf, name in sector_names.items():
        r = returns.get(etf)
        if not r:
            continue
        rel_s = r["ret_short"] - bench["ret_short"]
        rel_l = r["ret_long"] - bench["ret_long"]
        # Blend: recent relative strength weighted a bit more than the longer window.
        flow = round(0.6 * rel_s + 0.4 * rel_l, 2)
        direction = "inflow" if flow > thr else ("outflow" if flow < -thr else "neutral")
        rows.append({
            "sector": name,
            "etf": etf,
            "ret_short": round(r["ret_short"], 2),
            "ret_long": round(r["ret_long"], 2),
            "rel_short": round(rel_s, 2),
            "rel_long": round(rel_l, 2),
            "vol_ratio": r.get("vol_ratio"),
            "flow_score": flow,
            "direction": direction,
        })

    rows.sort(key=lambda x: -x["flow_score"])
    return {
        "benchmark": benchmark,
        "sectors": rows,
        "rotating_in": [r["sector"] for r in rows if r["direction"] == "inflow"],
        "rotating_out": [r["sector"] for r in rows if r["direction"] == "outflow"],
    }
