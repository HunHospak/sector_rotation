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


def build(cfg: dict) -> dict:
    sectors = cfg["sectors"]
    tickers = list(sectors.keys()) + [cfg["benchmark"]]
    returns = get_window_returns(tickers, int(cfg["window_short"]), int(cfg["window_long"]))
    data = analyze(returns, sectors, cfg["benchmark"], float(cfg["direction_threshold"]))
    data["as_of"] = dt.date.today().isoformat()
    data["window_short"] = int(cfg["window_short"])
    data["window_long"] = int(cfg["window_long"])

    status = "active" if data["sectors"] else "unavailable"
    feed = {
        "service": cfg["service"],
        "schema_version": str(cfg["schema_version"]),
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "ttl_hours": cfg["ttl_hours"],
        "data": data,
    }
    if status != "active":
        feed["notes"] = "no sector price data"
    return feed


def main() -> None:
    cfg = load_config()
    feed = build(cfg)
    jsonschema.validate(feed, load_schema())
    out = ROOT / "out"
    (out / "history").mkdir(parents=True, exist_ok=True)
    payload = json.dumps(feed, indent=2)
    (out / "sector_rotation.json").write_text(payload, encoding="utf-8")
    (out / "history" / f"{feed['data']['as_of']}.json").write_text(payload, encoding="utf-8")
    inn = ", ".join(feed["data"].get("rotating_in", [])) or "-"
    print(f"[sector_rotation] status={feed['status']} rotating_in: {inn}")


if __name__ == "__main__":
    main()
