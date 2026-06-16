"""24/7 runner: repeatedly scan, log opportunities, and alert.

Runs forever on an interval (default hourly). Persists found opportunities to a
JSONL log and optionally pushes alerts to a Slack/Discord webhook so the agent
literally works around the clock while you sleep.
"""

from __future__ import annotations

import json
import logging
import os
import signal
import time
from datetime import datetime, timezone
from pathlib import Path

from .adapters import get_marketplace
from .scanner import ScanConfig, scan

log = logging.getLogger("arbitrage.runner")


def _alert(message: str, webhook: str | None) -> None:
    if not webhook:
        return
    try:
        import requests

        requests.post(webhook, json={"text": message}, timeout=10)
    except Exception as exc:  # alerting must never crash the loop
        log.warning("alert failed: %s", exc)


def run_forever(
    *,
    source_name: str = "demo",
    target_name: str = "demo",
    config: ScanConfig | None = None,
    interval_seconds: int = 3600,
    query: str = "",
    out_dir: str = "runs",
    webhook: str | None = None,
    max_iterations: int | None = None,
    source_kwargs: dict | None = None,
    target_kwargs: dict | None = None,
) -> None:
    config = config or ScanConfig()
    webhook = webhook or os.environ.get("ALERT_WEBHOOK_URL")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    logfile = out / "opportunities.jsonl"

    source = get_marketplace(source_name, dataset="source", **(source_kwargs or {}))
    target = get_marketplace(target_name, dataset="target", **(target_kwargs or {}))

    stop = {"flag": False}

    def _handle(signum, _frame):
        log.info("received signal %s, shutting down after current cycle", signum)
        stop["flag"] = True

    try:
        signal.signal(signal.SIGINT, _handle)
        signal.signal(signal.SIGTERM, _handle)
    except (ValueError, OSError):
        pass  # not in main thread / unsupported platform

    iteration = 0
    while not stop["flag"]:
        iteration += 1
        ts = datetime.now(timezone.utc).isoformat()
        try:
            result = scan(source, target, config, query=query)
            profitable = result.profitable
            log.info(
                "cycle %d: scanned %d/%d, found %d profitable opportunities",
                iteration, result.scanned_source, result.scanned_target, len(profitable),
            )
            with logfile.open("a", encoding="utf-8") as fh:
                for opp in profitable:
                    fh.write(json.dumps({"ts": ts, **opp.as_row()}) + "\n")
            if profitable:
                top = profitable[0]
                _alert(
                    f"[arbitrage] {len(profitable)} opportunities. "
                    f"Top: {top.source.title[:50]} -> ${top.net_profit} "
                    f"profit ({top.roi*100:.0f}% ROI)",
                    webhook,
                )
        except Exception as exc:
            log.exception("scan cycle failed: %s", exc)
            _alert(f"[arbitrage] scan failed: {exc}", webhook)

        if max_iterations and iteration >= max_iterations:
            break
        if stop["flag"]:
            break
        time.sleep(interval_seconds)

    log.info("runner stopped after %d cycles", iteration)
