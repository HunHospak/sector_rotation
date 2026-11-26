"""Orchestration: ingest -> compute -> validate(schema) -> write out/."""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from providers import get_window_returns  # noqa: E402
from compute import analyze  # noqa: E402


def load_config() -> dict:
    return yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))


def load_schema() -> dict:
    return json.loads((ROOT / "schema.json").read_text(encoding="utf-8"))


def build(cfg: dict, *, generated_at: dt.datetime | None = None) -> dict:
    now = generated_at or dt.datetime.now(dt.timezone.utc)
    sectors = cfg["sectors"]
    benchmark = cfg["benchmark"]
    tickers = list(sectors.keys()) + [benchmark]
    returns = get_window_returns(tickers, int(cfg["window_short"]), int(cfg["window_long"]))
    benchmark_data = returns.get(benchmark)
    max_age_days = int(cfg.get("max_observation_age_days", 4))
    as_of = benchmark_data["as_of"] if benchmark_data else None
    benchmark_current = as_of and 0 <= (now.date() - dt.date.fromisoformat(as_of)).days <= max_age_days
    window_dates = ("as_of", "short_start", "long_start")
    aligned = {
        ticker: row for ticker, row in returns.items()
        if all(row[field] == benchmark_data[field] for field in window_dates)
    } if benchmark_current else {}

    data = analyze(aligned, sectors, benchmark, float(cfg["direction_threshold"]))
    data["as_of"] = as_of if benchmark_current else None
    data["window_short"] = int(cfg["window_short"])
    data["window_long"] = int(cfg["window_long"])

    if not benchmark_current:
        status, notes = "unavailable", f"No usable {benchmark} benchmark bars within {max_age_days} calendar days."
    elif not data["sectors"]:
        status, notes = "unavailable", f"No sector returns match the {benchmark} windows ending {as_of}."
    else:
        limitations = []
        if (now.date() - dt.date.fromisoformat(as_of)).days > 3:
            limitations.append(f"Latest usable {benchmark} benchmark bars are from {as_of}.")
        missing = sorted(set(sectors) - set(aligned))
        if missing:
            limitations.append(f"No returns aligned to the {benchmark} windows for: {', '.join(missing)}.")
        status, notes = ("partial", " ".join(limitations)) if limitations else ("active", None)
    feed = {
        "service": cfg["service"],
        "schema_version": str(cfg["schema_version"]),
        "generated_at": now.replace(microsecond=0).isoformat(),
        "status": status,
        "ttl_hours": cfg["ttl_hours"],
        "data": data,
    }
    if notes:
        feed["notes"] = notes
    return feed


def main() -> None:
    cfg = load_config()
    feed = build(cfg)
    jsonschema.validate(feed, load_schema())
    out = ROOT / "out"
    (out / "history").mkdir(parents=True, exist_ok=True)
    payload = json.dumps(feed, indent=2, allow_nan=False)
    (out / "sector_rotation.json").write_text(payload, encoding="utf-8")
    if feed["data"]["sectors"]:
        (out / "history" / f"{feed['data']['as_of']}.json").write_text(payload, encoding="utf-8")
    inn = ", ".join(feed["data"].get("rotating_in", [])) or "-"
    print(f"[sector_rotation] status={feed['status']} rotating_in: {inn}")


if __name__ == "__main__":
    main()
