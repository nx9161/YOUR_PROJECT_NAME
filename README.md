# Arbitrage Engine

A 24/7 automation that finds **resale / dropshipping arbitrage opportunities** and
generates optimized marketplace listings.

> **Honest expectations.** No software "prints" money. The profit in arbitrage
> comes from *you* buying goods cheaply and reselling them at a margin. What this
> engine automates is the slow, high-effort part: continuously scanning for price
> gaps, doing the profit math *after fees, shipping, and tax*, and drafting
> listings — so your ~$100 of inventory float works as hard as possible.
> Your realistic target ($1/hr ≈ $8,760/yr) requires real sales volume.

## What it does

1. **Scan** — pulls products from a *source* market (where you buy) and a
   *target* market (where you sell), matches them (by SKU/UPC or fuzzy title),
   and computes **net profit, ROI, and margin** after marketplace fees, payment
   fees, your shipping cost, and tax.
2. **Rank** — filters out money-losers and sorts winners by ROI.
3. **List** — generates keyword-optimized titles, descriptions, and a suggested
   price that hits your target margin (never below breakeven).
4. **Run 24/7** — repeats on an interval, logs opportunities to `runs/opportunities.jsonl`,
   and pushes alerts to a Slack/Discord webhook.

## Quick start (no API keys, works offline)

```bash
pip install -e .            # or: pip install -r requirements.txt

# Scan the bundled demo catalogs:
python -m arbitrage scan

# Generate listings for the top 5 opportunities:
python -m arbitrage listings --top 5

# Run against the free, live Fake Store API (still no keys):
python -m arbitrage scan --live

# Run it 24/7, scanning every hour:
python -m arbitrage run --interval 3600 --webhook https://hooks.slack.com/...
```

Example output:

```
sku      title                                 buy    sell   fees  ship  profit  roi_%  margin_%
WID-008 ...filtered (loss)...
WID-005 Resistance Bands Set 5 Levels Workout  4.1    15.99  2.42  5.0   4.47    109.0  28.0
...
```

## Real data sources

The engine is marketplace-agnostic via adapters in `arbitrage/adapters/`.
Three are built in: `demo`, `supplier` (your buy side), and `ebay` (your sell side).

### Supplier feed (your source / buy side) — no credentials

Point the `supplier` adapter at a real dropship/wholesale **CSV or JSON** feed
(local file or http(s) URL). Columns are matched case-insensitively with common
aliases (`sku|id`, `title|name`, `price|cost|wholesale_price`, `shipping`, etc.):

```bash
python -m arbitrage scan --source supplier --source-feed data/sample_supplier_feed.csv --target demo
# or a hosted feed:
python -m arbitrage scan --source supplier --source-feed https://my-supplier.com/feed.csv --target ebay
```

### eBay (your target / sell side) — official Browse API

1. Create a free app at https://developer.ebay.com → copy your **App ID**
   (client id) and **Cert ID** (client secret).
2. Set credentials (the adapter mints + caches the OAuth token for you):
   ```bash
   # macOS/Linux
   export EBAY_CLIENT_ID=...; export EBAY_CLIENT_SECRET=...
   # Windows PowerShell
   $env:EBAY_CLIENT_ID="..."; $env:EBAY_CLIENT_SECRET="..."
   ```
   (Or set `EBAY_OAUTH_TOKEN` directly if you already have a token.)
3. Scan a real supplier feed against live eBay sell prices:
   ```bash
   python -m arbitrage scan --source supplier --source-feed data/sample_supplier_feed.csv \
       --target ebay --query "wireless earbuds" --fees ebay
   ```

### Other marketplaces

Add an adapter implementing the `Marketplace` interface in
`arbitrage/adapters/base.py` and register it in `arbitrage/adapters/__init__.py`.
Fee schedules live in `arbitrage/fees.py`.

> Posting/transacting is intentionally **not** auto-executed — listing creation
> is an explicit, reviewable step. Only official, ToS-compliant APIs are used.
> Automating fake clicks on marketplaces gets accounts banned and can be illegal.

## Configuration

Copy `config/config.example.json` → `config/config.json` and adjust, or pass
flags directly (run `python -m arbitrage scan -h`). Key knobs:

| Flag | Meaning | Default |
|------|---------|---------|
| `--fees` | Fee schedule: `ebay`/`amazon`/`mercari`/`facebook`/`generic` | `ebay` |
| `--min-profit` | Minimum $ profit/unit to keep an opportunity | `1.0` |
| `--min-roi` | Minimum return on cost (0.15 = 15%) | `0.15` |
| `--ship` | Your shipping cost to the customer | `5.0` |
| `--interval` | Seconds between scans (run command) | `3600` |

## Development

```bash
pip install -e ".[dev]"
pytest           # run tests
ruff check .     # lint
```

## Roadmap

- Real Amazon SP-API + Mercari adapters
- UPC/EAN matching service for cross-market product identity
- Auto-draft eBay Sell API listings (human-approve before publish)
- Repricing daemon that reacts to competitor price changes
