"""Generate a ready-to-post social snippet from the latest feed."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    feed = json.loads((ROOT / "out" / "sector_rotation.json").read_text(encoding="utf-8"))
    d = feed["data"]
    rows = d.get("sectors", [])
    top = [row for row in rows if row["direction"] == "inflow"][:3]
    bottom = [row for row in reversed(rows) if row["direction"] == "outflow"][:3]

    lines = [f"Sector rotation — {d['as_of']} (vs {d.get('benchmark')}, rel. strength)" if d.get("as_of") else "Sector rotation"]
    if top:
        lines.append("Money leaning IN:")
        for r in top:
            lines.append(f"  ▲ {r['sector']} ({r['etf']})  flow {r['flow_score']:+.1f}")
    if bottom:
        lines.append("Leaning OUT:")
        for r in bottom:
            lines.append(f"  ▼ {r['sector']} ({r['etf']})  flow {r['flow_score']:+.1f}")
    if not rows:
        lines.append(feed.get("notes") or "Sector returns unavailable.")
    elif not (top or bottom):
        lines.append("No sector crossed the rotation threshold.")
    lines.append("Relative-strength proxy, not fund-flow data · not investment advice · arkenlabs.eu")

    text = "\n".join(lines)
    (ROOT / "out" / "post.txt").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
