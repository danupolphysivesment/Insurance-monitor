# -*- coding: utf-8 -*-
"""Config + .env loading with no third-party dependencies beyond PyYAML."""

from __future__ import annotations

import os
from typing import Dict

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(ROOT, "config.yml")
ENV_PATH = os.path.join(ROOT, ".env")

DEFAULTS: Dict = {
    "platforms": ["pantip", "x", "facebook", "threads", "reddit"],
    "results_per_query": 8,
    "freshness": "qdr:m",
    "alert_threshold": 50,
    "alert_channels": ["line", "telegram", "desktop"],
    "max_alerts_per_run": 8,
    "workers": 3,
    "queries": [],
    "reddit_queries": [],
}


def load_env(path: str = ENV_PATH) -> None:
    """Minimal .env reader — existing environment always wins."""
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val


def load_config(path: str = CONFIG_PATH) -> Dict:
    cfg = dict(DEFAULTS)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            loaded = yaml.safe_load(fh) or {}
        cfg.update({k: v for k, v in loaded.items() if v is not None})
    if not cfg.get("queries"):
        from .sources import DEFAULT_QUERIES
        cfg["queries"] = list(DEFAULT_QUERIES)
    if not cfg.get("reddit_queries"):
        from .sources import DEFAULT_REDDIT_QUERIES
        cfg["reddit_queries"] = list(DEFAULT_REDDIT_QUERIES)
    return cfg
