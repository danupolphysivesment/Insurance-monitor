# -*- coding: utf-8 -*-
"""Turns a raw social post into a scored, labelled insurance lead."""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Tuple

from . import keywords as K

TIERS = [(70, "HOT"), (45, "WARM"), (0, "COOL")]

# A post that never says "insurance" in any form is almost certainly noise,
# even if it hits life-event words ("pregnant", "bought a car").
INSURANCE_ANCHORS = ["ประกัน", "กรมธรรม์", "เบี้ย", "insurance", "policy", "premium"]


@dataclass
class Signals:
    intent: List[str] = field(default_factory=list)
    life_events: List[str] = field(default_factory=list)
    products: List[str] = field(default_factory=list)
    urgency: List[str] = field(default_factory=list)
    dissatisfaction: List[str] = field(default_factory=list)
    negatives: List[str] = field(default_factory=list)


def _hits(text: str, groups) -> List[Tuple[int, str]]:
    found = []
    for weight, patterns in groups:
        for p in patterns:
            if p.lower() in text:
                found.append((weight, p))
    return found


def _dedupe_by_weight(found: List[Tuple[int, str]], cap: int,
                      ceiling: int = 999) -> Tuple[int, List[str]]:
    """Sum the strongest `cap` distinct hits, clamped to `ceiling`.

    Overlapping phrases ("หาประกัน" and "กำลังหาประกัน") would otherwise let a
    single sentence stack the same signal several times over.
    """
    found = sorted(found, key=lambda x: -abs(x[0]))
    seen, total, labels = set(), 0, []
    for weight, pattern in found:
        if pattern in seen:
            continue
        seen.add(pattern)
        if len(labels) < cap:
            total += weight
            labels.append(pattern)
    if total > 0:
        total = min(total, ceiling)
    else:
        total = max(total, -ceiling)
    return total, labels


def classify_products(text: str) -> Tuple[int, List[str]]:
    score, found = 0, []
    for line, (weight, patterns) in K.PRODUCTS.items():
        if any(p.lower() in text for p in patterns):
            found.append(line)
            score += weight
    return min(score, 20), found


def score_post(title: str, snippet: str, url: str = "") -> Dict:
    """Return {'score', 'tier', 'products', 'signals', 'reasons', 'is_lead'}."""
    text = f"{title}\n{snippet}".lower()
    url_l = (url or "").lower()

    sig = Signals()
    reasons: List[str] = []
    score = 0

    has_anchor = any(a in text for a in INSURANCE_ANCHORS)

    pts, sig.intent = _dedupe_by_weight(_hits(text, K.INTENT), cap=3, ceiling=45)
    score += pts
    if pts:
        reasons.append(f"buying intent +{pts}")

    pts, sig.life_events = _dedupe_by_weight(_hits(text, K.LIFE_EVENTS), cap=3, ceiling=30)
    score += pts
    if pts:
        reasons.append(f"life event +{pts}")

    pts, products = classify_products(text)
    score += pts
    sig.products = products
    if pts:
        reasons.append(f"product named +{pts}")

    pts, sig.urgency = _dedupe_by_weight(_hits(text, K.URGENCY), cap=2, ceiling=10)
    score += pts
    if pts:
        reasons.append(f"urgency +{pts}")

    pts, sig.dissatisfaction = _dedupe_by_weight(_hits(text, K.DISSATISFACTION), cap=2, ceiling=15)
    score += pts
    if pts:
        reasons.append(f"unhappy with current cover +{pts}")

    # First person + a question = a human asking, not a brand broadcasting.
    first_person = any(w in text for w in [
        "เรา", "ผม", "ดิฉัน", "ตัวเอง", "ของผม", "ของเรา", "หนู", "ตนเอง",
        " i ", "i'm", "i am", "my ", "me ",
    ])
    asks = any(q in text for q in K.QUESTION_MARKERS)
    if first_person and asks:
        score += 12
        reasons.append("first-person question +12")
    elif asks:
        score += 6
        reasons.append("question form +6")

    pts, sig.negatives = _dedupe_by_weight(_hits(text, K.NEGATIVE), cap=3, ceiling=60)
    score += pts
    if pts:
        reasons.append(f"promo/news language {pts}")

    # Search returns image text as "OCR: …". People type their questions;
    # it is brochures and ad creatives that arrive as pictures.
    if snippet.strip().lower().startswith("ocr:"):
        score -= 30
        sig.negatives.append("OCR'd image (likely ad creative)")
        reasons.append("text came from an image -30")

    if any(d in url_l for d in K.BLOCKED_DOMAIN_PARTS):
        score -= 40
        sig.negatives.append("publisher/insurer domain")
        reasons.append("publisher or insurer domain -40")

    if not has_anchor:
        score -= 25
        reasons.append("no insurance keyword -25")

    score = max(0, min(100, score))
    tier = next(name for floor, name in TIERS if score >= floor)

    return {
        "score": score,
        "tier": tier,
        "products": products,
        "signals": asdict(sig),
        "reasons": reasons,
        "is_lead": score > 0 and has_anchor,
    }


def redact(text: str) -> str:
    """Strip contact details before anything is stored or pushed to a chat app.

    Public posts sometimes contain phone numbers or LINE IDs. We do not need
    them to triage a lead, and not keeping them is the whole point (PDPA).
    """
    text = re.sub(r"\b0\d[\d\- ]{7,11}\b", "[phone redacted]", text)
    text = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "[email redacted]", text)
    text = re.sub(r"(line\s*id|ไลน์ไอดี|ไอดีไลน์)\s*[:：]?\s*\S+",
                  r"\1 [redacted]", text, flags=re.I)
    return text
