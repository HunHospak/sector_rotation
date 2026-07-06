# sector_rotation

Independent ArkenLabs satellite service. Daily sector rotation via **relative strength**: each US
sector ETF vs the benchmark (SPY) on a short and long window, blended into a `flow_score` and an
`inflow / outflow / neutral` direction. Publishes one JSON feed the Arken research page consumes.

**Honest scope:** this is a transparent *proxy* for "where money is leaning", not true institutional
fund-flow data (that needs 13F / dark-pool feeds). The feed says so; the Arken panel shows it as such.

## Run locally
```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python src/build_feed.py       # writes out/sector_rotation.json + history
python scripts/post_text.py    # writes out/post.txt
```

## Configure
`config.yaml`: benchmark, windows (`window_short`, `window_long`), `direction_threshold`, and the
`sectors` map (ETF -> name). Add/remove sectors freely.

## Deploy
`.github/workflows/publish.yml` runs weekday cron, builds, and publishes `out/` to GitHub Pages:
`https://<user>.github.io/sector_rotation/sector_rotation.json`.

## Optional upgrade (later)
Blend in the PRISM `CF` (Capital Flow) + `SMS` (Smart Money) sector signals — but only by having
`project_prisma` export a **public** `cf_sms_by_sector.json`, which this service then *also consumes*.
That keeps both sides decoupled: sector_rotation stays a pure consumer, project_prisma stays a pure
publisher.

## Independence
Knows nothing about Arken. Arken knows only the feed URL + the shared schema. Either can change or die
without breaking the other.
