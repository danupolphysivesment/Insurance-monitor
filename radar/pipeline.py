# -*- coding: utf-8 -*-
"""One scan: collect -> score -> dedupe -> store -> alert."""

from __future__ import annotations

from typing import Callable, Dict, List, Optional

from . import notify, sources, store
from .scoring import redact, score_post


def run_scan(conn, cfg: Dict, on_progress: Optional[Callable[[str], None]] = None,
             dry_run: bool = False) -> Dict:
    """Execute a full scan. Returns a summary dict for the caller to display."""
    platforms = cfg.get("platforms") or ["pantip"]

    posts, errors = sources.collect(
        platforms=platforms,
        queries=cfg.get("queries", []),
        limit=int(cfg.get("results_per_query", 8)),
        freshness=cfg.get("freshness", "qdr:m") or "",
        reddit_queries=cfg.get("reddit_queries", []),
        on_progress=on_progress,
        workers=int(cfg.get("workers", 3)),
    )

    threshold = int(cfg.get("alert_threshold", 60))
    new_leads: List[Dict] = []
    all_scored: List[Dict] = []

    for post in posts:
        verdict = score_post(post.title, post.snippet, post.url)
        if not verdict["is_lead"]:
            continue
        lead = {
            "url": post.url,
            "platform": post.platform,
            "title": redact(post.title),
            "snippet": redact(post.snippet),
            "query": post.query,
            **verdict,
        }
        all_scored.append(lead)
        if dry_run:
            continue
        if store.upsert_lead(conn, lead):
            lead["id"] = store.lead_id(lead["url"])
            new_leads.append(lead)

    alertable = sorted([l for l in new_leads if l["score"] >= threshold],
                       key=lambda l: -l["score"])
    capped = alertable[: int(cfg.get("max_alerts_per_run", 8))]

    results: Dict[str, str] = {}
    if capped and not dry_run:
        results = notify.dispatch(capped, cfg.get("alert_channels"))
        store.mark_alerted(conn, [l["id"] for l in capped])

    if not dry_run:
        store.log_run(conn, platforms, len(posts), len(new_leads),
                      len(alertable), errors)

    return {
        "scanned": len(posts),
        "scored": len(all_scored),
        "new_leads": len(new_leads),
        "alertable": len(alertable),
        "alerted": len(capped),
        "channels": results,
        "errors": errors,
        "top": sorted(all_scored, key=lambda l: -l["score"])[:20],
    }
