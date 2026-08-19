# -*- coding: utf-8 -*-
"""Collectors: public social/forum posts via the Firecrawl CLI.

Only publicly indexed pages are read. Nothing here logs in, joins a private
group, or touches anything behind a login wall.
"""

from __future__ import annotations

import json
import random
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Dict, Iterable, List
from urllib.parse import urlparse

from .keywords import BLOCKED_HANDLES

# A real post lives at a post-shaped URL. Profile pages, tag pages and
# hub pages are noise, and they are the bulk of what search returns.
URL_MUST_CONTAIN = {
    "x.com": "/status/",
    "twitter.com": "/status/",
    "pantip.com": "/topic/",
    "reddit.com": "/comments/",
    "threads.net": "/post/",
    "tiktok.com": "/video/",
}
URL_REJECT_PARTS = [
    "/tag/", "/search", "/explore", "/hashtag/", "/help/", "/policies",
    "/terms", "/privacy", "/business", "/ads/", "/login", "/pages/category",
]


def _is_post_url(url: str) -> bool:
    low = url.lower()
    host = urlparse(low).netloc.replace("www.", "")
    for domain, needle in URL_MUST_CONTAIN.items():
        if host.endswith(domain) and needle not in low:
            return False
    if any(part in low for part in URL_REJECT_PARTS):
        return False
    return not any(f"/{h}" in low or f"@{h}" in low for h in BLOCKED_HANDLES)

FIRECRAWL = shutil.which("firecrawl") or "firecrawl"


@dataclass
class RawPost:
    url: str
    title: str
    snippet: str
    platform: str
    query: str


PLATFORMS: Dict[str, Dict] = {
    "pantip": {
        "label": "Pantip",
        "site": "pantip.com",
        "country": "TH",
        "enabled": True,
    },
    "x": {
        "label": "X / Twitter",
        "site": "x.com",
        "country": "TH",
        "enabled": True,
    },
    "facebook": {
        "label": "Facebook (public)",
        "site": "facebook.com",
        "country": "TH",
        "enabled": True,
    },
    "threads": {
        "label": "Threads",
        "site": "threads.net",
        "country": "TH",
        "enabled": True,
    },
    "blockdit": {
        "label": "Blockdit",
        "site": "blockdit.com",
        "country": "TH",
        "enabled": False,
    },
    "reddit": {
        "label": "Reddit",
        "site": "reddit.com",
        "country": "TH",
        "enabled": True,
    },
    "tiktok": {
        "label": "TikTok",
        "site": "tiktok.com",
        "country": "TH",
        "enabled": False,
    },
}

# Query packs. Each string is combined with `site:<platform>` at run time.
# Written the way people actually type, not the way marketers do.
DEFAULT_QUERIES: List[str] = [
    "อยากทำประกันสุขภาพ แนะนำ",
    "ประกันสุขภาพ เหมาจ่าย เจ้าไหนดี",
    "กำลังมองหาประกันชีวิต ควรทำไหม",
    "ประกันโรคร้ายแรง แนะนำ ตัวไหนดี",
    "เพิ่งเริ่มทำงาน ควรทำประกันอะไรก่อน",
    "ท้อง ประกันสุขภาพ ค่าคลอด แนะนำ",
    "ลาออกจากงาน ประกันกลุ่มหมด ทำประกันเอง",
    "ประกันลดหย่อนภาษี ปีนี้ ตัวไหนดี",
    "ประกันบำนาญ วางแผนเกษียณ แนะนำ",
    "ประกันรถยนต์ ชั้น 1 เจ้าไหนดี ราคา",
    "ประกันเดินทาง ต่างประเทศ วีซ่า แนะนำ",
    "ประกันสุขภาพให้พ่อแม่ ผู้สูงอายุ แนะนำ",
    "เคลมประกันไม่ผ่าน อยากเปลี่ยนบริษัท",
    "ทำประกันสุขภาพให้ลูก แนะนำ",
    "ยูนิตลิงค์ ดีไหม ควรทำ",
    "health insurance Thailand which one recommend expat",
]

DEFAULT_REDDIT_QUERIES: List[str] = [
    "health insurance Thailand recommend which company",
    "life insurance advice should I buy",
    "expat insurance Thailand looking for",
]


def _run_firecrawl(query: str, limit: int, country: str, tbs: str,
                   timeout: int = 90, retries: int = 4) -> List[Dict]:
    """One search, with backoff on rate limits.

    Firecrawl rate-limits by plan, and a parallel sweep hits 429 readily. A
    429 that is not retried loses a whole platform's worth of queries without
    anything obviously breaking, so retrying matters more than speed here.
    """
    cmd = [FIRECRAWL, "search", query, "--limit", str(limit),
           "--country", country, "--json"]
    if tbs:
        cmd += ["--tbs", tbs]

    last_err = "unknown error"
    for attempt in range(retries):
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            raise RuntimeError(f"firecrawl failed: {exc}") from exc
        if out.returncode == 0:
            break
        last_err = (out.stderr or out.stdout or "unknown error").strip()[:400]
        rate_limited = "429" in last_err or "rate limit" in last_err.lower()
        if not rate_limited or attempt == retries - 1:
            raise RuntimeError(last_err)
        # 6s, 15s, 33s plus jitter so retries don't resynchronise into a burst
        time.sleep((6 * (2.5 ** attempt)) + random.uniform(0, 3))
    else:  # pragma: no cover - loop always breaks or raises
        raise RuntimeError(last_err)

    text = out.stdout.strip()
    start = text.find("{")
    if start < 0:
        return []
    payload = json.loads(text[start:])
    return payload.get("data", {}).get("web", []) or []


def collect(platforms: Iterable[str], queries: Iterable[str],
            limit: int = 8, freshness: str = "qdr:m",
            reddit_queries: Iterable[str] | None = None,
            on_progress=None, workers: int = 3) -> tuple[List[RawPost], List[str]]:
    """Run every (platform x query) pair and return normalised posts + errors.

    Each pair is an independent subprocess waiting on the network, so they run
    in a small thread pool — serial execution puts a full sweep past ten
    minutes, which is too slow to sit in front of in the dashboard.
    """
    queries = list(queries)
    reddit_queries = list(reddit_queries or DEFAULT_REDDIT_QUERIES)

    jobs = []
    for key in platforms:
        meta = PLATFORMS.get(key)
        if not meta:
            continue
        for q in (reddit_queries if key == "reddit" else queries):
            jobs.append((key, meta, q))

    posts: List[RawPost] = []
    errors: List[str] = []
    seen_urls = set()

    def fetch(job):
        key, meta, q = job
        full = f"site:{meta['site']} {q}"
        try:
            return job, _run_firecrawl(full, limit, meta["country"], freshness), None
        except RuntimeError as exc:
            return job, [], str(exc)

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = []
        for job in jobs:
            futures.append(pool.submit(fetch, job))
            time.sleep(0.35)   # stagger the opening burst
        for done, future in enumerate(as_completed(futures), start=1):
            (key, meta, q), results, err = future.result()
            if on_progress:
                on_progress(f"{done}/{len(jobs)} · {meta['label']} · {q[:38]}")
            if err:
                errors.append(f"{meta['label']} / {q[:30]}: {err}")
                continue
            for r in results:
                url = (r.get("url") or "").split("#")[0].rstrip("/")
                if not url or url in seen_urls or not _is_post_url(url):
                    continue
                # Firecrawl sometimes returns both /topic/N and /topic/N/desktop
                canon = url.replace("/desktop", "").replace("/mobile", "")
                if canon in seen_urls:
                    continue
                seen_urls.add(url)
                seen_urls.add(canon)
                host = urlparse(url).netloc.replace("www.", "")
                posts.append(RawPost(
                    url=canon,
                    title=(r.get("title") or "").strip(),
                    snippet=(r.get("description") or "")[:1200].strip(),
                    platform=key if meta["site"] in host else host,
                    query=q,
                ))
    return posts, errors
