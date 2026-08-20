# -*- coding: utf-8 -*-
"""Collectors: public social/forum posts via the Firecrawl CLI.

Only publicly indexed pages are read. Nothing here logs in, joins a private
group, or touches anything behind a login wall.
"""

from __future__ import annotations

import functools
import json
import os
import random
import shutil
import subprocess
import time
import urllib.error
import urllib.request
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

# Where package managers put the CLI. A GUI-launched Streamlit process does not
# inherit your shell's PATH, so `which` alone is not enough to find it.
_BIN_DIRS = [
    "/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/opt/local/bin",
    os.path.expanduser("~/.local/bin"),
    os.path.expanduser("~/.npm-global/bin"),
    os.path.expanduser("~/.volta/bin"),
    os.path.expanduser("~/.bun/bin"),
    os.path.expanduser("~/.yarn/bin"),
    os.path.expanduser("~/n/bin"),
]

MISSING_CLI_HINT = (
    "firecrawl CLI not found. Install it with `npm i -g firecrawl-cli` and "
    "authenticate, or set FIRECRAWL_BIN to its full path (find it with "
    "`which firecrawl`)."
)

API_URL = os.getenv("FIRECRAWL_API_URL", "https://api.firecrawl.dev").rstrip("/")


@functools.lru_cache(maxsize=1)
def firecrawl_bin() -> str:
    """Locate the firecrawl CLI, resolved lazily and cached.

    Resolving at import time was a bug: Streamlit launched from a GUI has a
    narrower PATH than the shell, so the lookup failed once and every later
    search inherited the failure.
    """
    override = os.getenv("FIRECRAWL_BIN", "").strip()
    if override:
        if os.path.isfile(override) and os.access(override, os.X_OK):
            return override
        raise RuntimeError(f"FIRECRAWL_BIN is set to '{override}', which is not "
                           f"an executable file.")

    found = shutil.which("firecrawl")
    if found:
        return found

    for directory in _BIN_DIRS:
        candidate = os.path.join(directory, "firecrawl")
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            # Put it on PATH too, so anything else we shell out to can see it.
            os.environ["PATH"] = directory + os.pathsep + os.environ.get("PATH", "")
            return candidate

    raise RuntimeError(MISSING_CLI_HINT)


def _search_http(query: str, limit: int, country: str, tbs: str,
                 timeout: int = 45) -> List[Dict]:  # noqa: D401
    """Search over Firecrawl's REST API — no CLI, no PATH, no Node.

    This is the only transport that works on a hosted box such as Streamlit
    Cloud, where the Node CLI cannot be installed at all.
    """
    body: Dict = {"query": query, "limit": limit, "sources": ["web"]}
    if country:
        body["location"] = country
    if tbs:
        body["tbs"] = tbs

    req = urllib.request.Request(f"{API_URL}/v2/search",
                                 data=json.dumps(body).encode("utf-8"),
                                 method="POST")
    req.add_header("Content-Type", "application/json")
    key = os.getenv("FIRECRAWL_API_KEY", "").strip()
    if key:
        req.add_header("Authorization", f"Bearer {key}")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8", "ignore"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "ignore")[:200]
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except Exception as exc:
        raise RuntimeError(str(exc)[:200]) from exc

    data = payload.get("data")
    if isinstance(data, dict):          # v2 shape: {"data": {"web": [...]}}
        return data.get("web") or []
    return data or []                   # v1 shape: {"data": [...]}


def backend() -> str:
    """Which transport to use: 'http' or 'cli'.

    An explicit API key wins, because that is the deliberate choice. Otherwise
    the local CLI is preferred since it carries your authenticated plan. With
    neither, fall back to the unauthenticated API so a fresh deploy still runs.
    """
    if os.getenv("FIRECRAWL_API_KEY", "").strip():
        return "http"
    try:
        firecrawl_bin()
        return "cli"
    except RuntimeError:
        return "http"


def backend_status() -> tuple[bool, str]:
    """(ok, human-readable description) for the dashboard to show up front."""
    if backend() == "http":
        if os.getenv("FIRECRAWL_API_KEY", "").strip():
            return True, f"Firecrawl API (authenticated) · {API_URL}"
        return True, (f"Firecrawl API (no key — usage-limited) · {API_URL}. "
                      "Set FIRECRAWL_API_KEY for full limits.")
    return True, f"firecrawl CLI · {firecrawl_bin()}"


# Kept so a half-updated deployment does not crash on import-time attribute
# lookup. Older app.py calls this name.
cli_status = backend_status


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


def _search_cli(query: str, limit: int, country: str, tbs: str,
                timeout: int) -> List[Dict]:
    """Search by shelling out to the local, already-authenticated CLI."""
    cmd = [firecrawl_bin(), "search", query, "--limit", str(limit),
           "--country", country, "--json"]
    if tbs:
        cmd += ["--tbs", tbs]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        raise RuntimeError(f"firecrawl failed: {exc}") from exc
    if out.returncode != 0:
        raise RuntimeError((out.stderr or out.stdout or "unknown error").strip()[:400])

    text = out.stdout.strip()
    start = text.find("{")
    if start < 0:
        return []
    payload = json.loads(text[start:])
    return payload.get("data", {}).get("web", []) or []


def _run_firecrawl(query: str, limit: int, country: str, tbs: str,
                   timeout: int = 45, retries: int = 3) -> List[Dict]:
    """One search through whichever transport is available, with 429 backoff.

    Firecrawl rate-limits by plan and a parallel sweep hits 429 readily. A 429
    that is not retried loses a whole platform's worth of queries without
    anything obviously breaking, so both transports share this retry loop.
    """
    search = _search_http if backend() == "http" else _search_cli

    last_err = "unknown error"
    for attempt in range(retries):
        try:
            return search(query, limit, country, tbs, timeout)
        except RuntimeError as exc:
            last_err = str(exc)
            rate_limited = "429" in last_err or "rate limit" in last_err.lower()
            if not rate_limited or attempt == retries - 1:
                raise
            # 4s, 9s plus jitter so retries don't resynchronise into a burst.
            # Kept short on purpose: a stalled worker shows up as a frozen
            # progress bar, and a search still 429ing after ~15s is better
            # reported than waited on.
            time.sleep((4 * (2.25 ** attempt)) + random.uniform(0, 2))
    raise RuntimeError(last_err)  # pragma: no cover - loop returns or raises


def collect(platforms: Iterable[str], queries: Iterable[str],
            limit: int = 8, freshness: str = "qdr:m",
            reddit_queries: Iterable[str] | None = None,
            on_progress=None, workers: int = 3) -> tuple[List[RawPost], List[str]]:
    """Run every (platform x query) pair and return normalised posts + errors.

    Each pair is an independent subprocess waiting on the network, so they run
    in a small thread pool — serial execution puts a full sweep past ten
    minutes, which is too slow to sit in front of in the dashboard.
    """
    backend_status()  # raises once, with a fix, instead of failing per query

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
