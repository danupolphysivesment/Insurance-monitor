#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Insurance Lead Radar — command line runner.

  python run_radar.py --once              one scan, alert, exit
  python run_radar.py --loop 30           scan every 30 minutes
  python run_radar.py --dry-run           score and print, store nothing
  python run_radar.py --test-alert        prove your LINE/Telegram wiring works
  python run_radar.py --rescore --purge  re-grade stored leads after tuning
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime

from radar import notify, store
from radar.config import load_config, load_env
from radar.pipeline import run_scan

TIER_ICON = {"HOT": "\033[91mHOT \033[0m", "WARM": "\033[93mWARM\033[0m",
             "COOL": "\033[96mCOOL\033[0m"}


def _print_summary(res: dict) -> None:
    print(f"  scanned {res['scanned']} posts · {res['scored']} scored as leads "
          f"· {res['new_leads']} new · {res['alertable']} above threshold "
          f"· {res['alerted']} alerted")
    for lead in res["top"][:10]:
        prods = ",".join(lead["products"]) or "-"
        print(f"   {TIER_ICON.get(lead['tier'], lead['tier'])} {lead['score']:3} "
              f"[{lead['platform']:9}] {prods:16} {lead['title'][:56]}")
        print(f"        {lead['url']}")
    for chan, result in (res.get("channels") or {}).items():
        print(f"   alert · {chan}: {result}")
    for err in res["errors"][:5]:
        print(f"   \033[90mwarn: {err}\033[0m")


def main() -> int:
    ap = argparse.ArgumentParser(description="Insurance lead radar")
    ap.add_argument("--once", action="store_true", help="run a single scan")
    ap.add_argument("--loop", type=int, metavar="MINUTES",
                    help="scan repeatedly every N minutes")
    ap.add_argument("--dry-run", action="store_true",
                    help="score and print without storing or alerting")
    ap.add_argument("--test-alert", action="store_true",
                    help="send one fake lead through every configured channel")
    ap.add_argument("--rescore", action="store_true",
                    help="re-grade stored leads after editing keywords.py")
    ap.add_argument("--purge", action="store_true",
                    help="with --rescore, delete untriaged leads that now score 0")
    ap.add_argument("--threshold", type=int, help="override alert threshold")
    ap.add_argument("--platforms", help="comma separated override, e.g. pantip,x")
    args = ap.parse_args()

    load_env()
    cfg = load_config()
    if args.threshold is not None:
        cfg["alert_threshold"] = args.threshold
    if args.platforms:
        cfg["platforms"] = [p.strip() for p in args.platforms.split(",") if p.strip()]

    if args.test_alert:
        fake = [{
            "title": "ทดสอบระบบ: อยากทำประกันสุขภาพ แนะนำหน่อยครับ",
            "url": "https://pantip.com/topic/00000000",
            "platform": "pantip", "score": 88, "tier": "HOT",
            "products": ["health"],
        }]
        for chan, result in notify.dispatch(fake, cfg.get("alert_channels")).items():
            print(f"{chan:9} -> {result}")
        return 0

    conn = store.connect()

    if args.rescore:
        stats = store.rescore_all(conn)
        print(f"rescored {stats['total']} leads · {stats['changed']} changed "
              f"· {stats['zeroed']} fell to zero")
        if args.purge:
            print(f"purged {store.purge_zero_scores(conn)} untriaged zero-score leads")
        return 0

    def scan() -> None:
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        print(f"\n\033[1m[{stamp}] scanning {','.join(cfg['platforms'])}\033[0m")
        res = run_scan(conn, cfg,
                       on_progress=lambda m: print(f"   … {m}", flush=True),
                       dry_run=args.dry_run)
        _print_summary(res)

    if args.loop:
        print(f"radar running every {args.loop} min — ctrl-c to stop")
        while True:
            try:
                scan()
            except KeyboardInterrupt:
                print("\nstopped")
                return 0
            except Exception as exc:  # keep the loop alive through transient errors
                print(f"   \033[91mscan failed: {exc}\033[0m")
            time.sleep(args.loop * 60)

    scan()
    return 0


if __name__ == "__main__":
    sys.exit(main())
