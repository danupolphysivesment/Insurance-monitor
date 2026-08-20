# -*- coding: utf-8 -*-
"""Alert channels: LINE, Telegram, generic webhook, macOS banner.

Every channel is optional and configured by env var. Anything unconfigured is
silently skipped, so the radar still runs with no setup at all.

NOTE ON LINE: LINE Notify (notify-bot.line.me) was shut down on 2025-03-31.
The working path today is the Messaging API — create a free LINE Official
Account, add yourself as a friend, and push to yourself. That is what this
module uses.
"""

from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request
from typing import Dict, List

TIER_ICON = {"HOT": "🔥", "WARM": "🌤", "COOL": "🧊"}
PRODUCT_TH = {
    "health": "สุขภาพ", "critical_illness": "โรคร้ายแรง", "life": "ชีวิต",
    "motor": "รถยนต์", "travel": "เดินทาง", "accident_pa": "อุบัติเหตุ",
    "savings_annuity": "ออม/บำนาญ", "home_fire": "บ้าน/อัคคีภัย",
}


def _post_json(url: str, payload: Dict, headers: Dict | None = None,
               timeout: int = 15) -> tuple[bool, str]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 300, f"{resp.status}"
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}: {exc.read().decode('utf-8', 'ignore')[:200]}"
    except Exception as exc:  # network, DNS, timeout
        return False, str(exc)[:200]


# ------------------------------------------------------------------ text ----
def format_lead_line(lead: Dict) -> str:
    icon = TIER_ICON.get(lead["tier"], "•")
    prods = ", ".join(PRODUCT_TH.get(p, p) for p in lead.get("products", [])) or "ไม่ระบุ"
    title = lead["title"][:90]
    return (f"{icon} {lead['score']}/100 · {lead['platform']} · {prods}\n"
            f"{title}\n{lead['url']}")


def format_digest(leads: List[Dict], max_items: int = 8) -> str:
    head = f"🛟 พบโพสต์ที่น่าจะต้องการประกัน {len(leads)} รายการ"
    body = "\n\n".join(format_lead_line(l) for l in leads[:max_items])
    tail = ""
    if len(leads) > max_items:
        tail = f"\n\n…และอีก {len(leads) - max_items} รายการ (ดูใน dashboard)"
    return f"{head}\n\n{body}{tail}"


# ------------------------------------------------------------------ LINE ----
def send_line(text: str, leads: List[Dict] | None = None) -> tuple[bool, str]:
    token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "").strip()
    if not token:
        return False, "skipped (no LINE_CHANNEL_ACCESS_TOKEN)"
    to = os.getenv("LINE_TO", "").strip()

    # One message per alert, deliberately: LINE's free Official Account tier
    # allows only ~200 pushes a month, so a Flex card that carries every lead
    # beats a card plus a text digest.
    messages: List[Dict] = [{"type": "text", "text": text[:4900]}]
    if leads:
        bubble = _flex_bubble(leads[:8])
        if bubble:
            messages = [bubble]

    headers = {"Authorization": f"Bearer {token}"}
    if to:
        return _post_json("https://api.line.me/v2/bot/message/push",
                          {"to": to, "messages": messages}, headers)
    # No user id configured: broadcast to everyone who added the OA (i.e. you).
    return _post_json("https://api.line.me/v2/bot/message/broadcast",
                      {"messages": messages}, headers)


def _flex_bubble(leads: List[Dict]) -> Dict | None:
    """A compact Flex card so LINE shows tappable leads, not a wall of text."""
    rows = []
    for l in leads:
        icon = TIER_ICON.get(l["tier"], "•")
        prods = ", ".join(PRODUCT_TH.get(p, p) for p in l.get("products", []))
        rows.append({
            "type": "box", "layout": "vertical", "margin": "md", "spacing": "xs",
            "action": {"type": "uri", "label": "open", "uri": l["url"]},
            "contents": [
                {"type": "text", "size": "sm", "weight": "bold", "wrap": True,
                 "text": f"{icon} {l['score']} · {l['title'][:70]}"},
                {"type": "text", "size": "xxs", "color": "#8c8c8c", "wrap": True,
                 "text": f"{l['platform']} · {prods or 'ไม่ระบุประเภท'}"},
            ],
        })
    if not rows:
        return None
    return {
        "type": "flex",
        "altText": f"พบ {len(leads)} โพสต์ที่น่าจะต้องการประกัน",
        "contents": {
            "type": "bubble",
            "header": {"type": "box", "layout": "vertical", "contents": [
                {"type": "text", "text": "Insurance Lead Radar", "weight": "bold",
                 "size": "sm", "color": "#1a5f4a"},
                {"type": "text", "text": f"{len(leads)} โพสต์ใหม่ที่เข้าเกณฑ์",
                 "size": "xs", "color": "#8c8c8c"},
            ]},
            "body": {"type": "box", "layout": "vertical", "spacing": "sm",
                     "contents": rows},
        },
    }


# -------------------------------------------------------------- Telegram ----
def send_telegram(text: str) -> tuple[bool, str]:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not (token and chat):
        return False, "skipped (no TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID)"
    return _post_json(f"https://api.telegram.org/bot{token}/sendMessage",
                      {"chat_id": chat, "text": text[:4000],
                       "disable_web_page_preview": True})


# ---------------------------------------------------------------- webhook ---
def send_webhook(text: str) -> tuple[bool, str]:
    url = os.getenv("WEBHOOK_URL", "").strip()
    if not url:
        return False, "skipped (no WEBHOOK_URL)"
    # Discord wants "content", Slack wants "text" — send both keys.
    return _post_json(url, {"content": text[:1900], "text": text[:1900]})


# ----------------------------------------------------------------- macOS ----
def send_desktop(title: str, body: str) -> tuple[bool, str]:
    if os.uname().sysname != "Darwin":
        return False, "skipped (not macOS)"
    safe = body.replace('"', "'")[:200]
    try:
        subprocess.run(
            ["osascript", "-e",
             f'display notification "{safe}" with title "{title}" sound name "Glass"'],
            capture_output=True, timeout=10)
        return True, "ok"
    except Exception as exc:
        return False, str(exc)[:120]


# ------------------------------------------------------------------ fanout --
def dispatch(leads: List[Dict], channels: List[str] | None = None) -> Dict[str, str]:
    """Send one digest to every enabled channel. Returns {channel: result}."""
    if not leads:
        return {}
    channels = channels or ["line", "telegram", "webhook", "desktop"]
    text = format_digest(leads)
    results: Dict[str, str] = {}
    if "line" in channels:
        ok, msg = send_line(text, leads)
        results["line"] = "sent" if ok else msg
    if "telegram" in channels:
        ok, msg = send_telegram(text)
        results["telegram"] = "sent" if ok else msg
    if "webhook" in channels:
        ok, msg = send_webhook(text)
        results["webhook"] = "sent" if ok else msg
    if "desktop" in channels:
        top = leads[0]
        ok, msg = send_desktop(
            f"🛟 {len(leads)} insurance lead(s)",
            f"{top['score']}/100 · {top['title'][:80]}")
        results["desktop"] = "sent" if ok else msg
    return results
