"""Command-line interface for the arbitrage engine.

Examples
--------
# See profitable opportunities using the offline demo data:
python -m arbitrage scan --source demo --target demo

# Run live against the free Fake Store API (no keys needed):
python -m arbitrage scan --live

# Generate optimized listings for the winners:
python -m arbitrage listings --top 5

# Run 24/7, scanning every hour, logging + alerting:
python -m arbitrage run --interval 3600
"""

from __future__ import annotations

import argparse
import json
import logging
import sys

from .adapters import get_marketplace
from .listing import make_listing
from .scanner import ScanConfig, scan


def _build_config(args) -> ScanConfig:
    return ScanConfig(
        fee_schedule=args.fees,
        min_profit=args.min_profit,
        min_roi=args.min_roi,
        ship_to_customer=args.ship,
        units=args.units,
        limit=args.limit,
    )


def _make_markets(args):
    src_kwargs = {"dataset": "source"}
    tgt_kwargs = {"dataset": "target"}
    if args.source == "demo":
        src_kwargs["live"] = args.live
    if args.target == "demo":
        tgt_kwargs["live"] = args.live
    source = get_marketplace(args.source, **src_kwargs)
    target = get_marketplace(args.target, **tgt_kwargs)
    return source, target


def _print_table(rows: list[dict]) -> None:
    if not rows:
        print("No profitable opportunities found with current thresholds.")
        return
    headers = list(rows[0].keys())
    widths = {h: max(len(h), *(len(str(r[h])) for r in rows)) for h in headers}
    line = "  ".join(h.ljust(widths[h]) for h in headers)
    print(line)
    print("-" * len(line))
    for r in rows:
        print("  ".join(str(r[h]).ljust(widths[h]) for h in headers))


def cmd_scan(args) -> int:
    source, target = _make_markets(args)
    result = scan(source, target, _build_config(args), query=args.query)
    rows = [o.as_row() for o in result.opportunities]
    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        print(
            f"Scanned {result.scanned_source} source / {result.scanned_target} target products.\n"
        )
        _print_table(rows)
        total = sum(o.net_profit for o in result.opportunities)
        print(f"\nTotal projected profit across {len(rows)} opportunities: ${total:.2f}")
    return 0


def cmd_listings(args) -> int:
    source, target = _make_markets(args)
    result = scan(source, target, _build_config(args), query=args.query)
    listings = [make_listing(o, args.fees).to_dict() for o in result.opportunities[: args.top]]
    print(json.dumps(listings, indent=2))
    return 0


def cmd_run(args) -> int:
    from .runner import run_forever

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    src_kwargs = {"live": args.live} if args.source == "demo" else {}
    tgt_kwargs = {"live": args.live} if args.target == "demo" else {}
    run_forever(
        source_name=args.source,
        target_name=args.target,
        config=_build_config(args),
        interval_seconds=args.interval,
        query=args.query,
        webhook=args.webhook,
        max_iterations=args.max_iterations,
        source_kwargs=src_kwargs,
        target_kwargs=tgt_kwargs,
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="arbitrage", description="Find resale arbitrage and generate listings.")
    sub = p.add_subparsers(dest="command", required=True)

    def common(sp):
        sp.add_argument("--source", default="demo", help="source marketplace (buy)")
        sp.add_argument("--target", default="demo", help="target marketplace (sell)")
        sp.add_argument("--query", default="", help="search query (blank = browse catalog)")
        sp.add_argument("--fees", default="ebay", help="fee schedule: ebay/amazon/mercari/facebook/generic")
        sp.add_argument("--min-profit", type=float, default=1.0, dest="min_profit")
        sp.add_argument("--min-roi", type=float, default=0.15, dest="min_roi")
        sp.add_argument("--ship", type=float, default=5.0, help="your shipping cost to customer")
        sp.add_argument("--units", type=int, default=1)
        sp.add_argument("--limit", type=int, default=200)
        sp.add_argument("--live", action="store_true", help="use live Fake Store API (demo markets only)")

    sp_scan = sub.add_parser("scan", help="scan and rank opportunities")
    common(sp_scan)
    sp_scan.add_argument("--json", action="store_true")
    sp_scan.set_defaults(func=cmd_scan)

    sp_list = sub.add_parser("listings", help="generate listings for top opportunities")
    common(sp_list)
    sp_list.add_argument("--top", type=int, default=5)
    sp_list.set_defaults(func=cmd_listings)

    sp_run = sub.add_parser("run", help="run 24/7 on an interval")
    common(sp_run)
    sp_run.add_argument("--interval", type=int, default=3600, help="seconds between scans")
    sp_run.add_argument("--webhook", default=None, help="Slack/Discord webhook for alerts")
    sp_run.add_argument("--max-iterations", type=int, default=None, dest="max_iterations")
    sp_run.set_defaults(func=cmd_run)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv if argv is not None else sys.argv[1:])
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
