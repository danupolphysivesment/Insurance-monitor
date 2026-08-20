# -*- coding: utf-8 -*-
"""Insurance Lead Radar — triage dashboard.

    streamlit run app.py --server.port 8580
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from radar import notify, sources, store          # noqa: E402
from radar.config import load_config, load_env    # noqa: E402
from radar.pipeline import run_scan               # noqa: E402

st.set_page_config(page_title="Insurance Lead Radar", page_icon="🛟",
                   layout="wide", initial_sidebar_state="expanded")

INK, PAPER, ACCENT = "#14201c", "#f7f5f0", "#1a5f4a"
TIER_COLOR = {"HOT": "#b3341f", "WARM": "#c68b2c", "COOL": "#5b7f93"}

st.markdown(f"""
<style>
  .stApp {{ background:{PAPER}; }}
  html, body, [class*="css"] {{ font-family:-apple-system,"Helvetica Neue",sans-serif; }}
  .masthead {{ border-bottom:2px solid {INK}; padding-bottom:.5rem; margin-bottom:1.2rem; }}
  .masthead h1 {{ font-size:2.1rem; letter-spacing:-.02em; margin:0; color:{INK};
                  font-weight:800; }}
  .masthead p {{ margin:.25rem 0 0; color:#6b7671; font-size:.83rem;
                 text-transform:uppercase; letter-spacing:.13em; }}
  .lead {{ background:#fff; border:1px solid #e2ded4; border-left:4px solid #ccc;
           border-radius:3px; padding:.85rem 1rem; margin-bottom:.6rem; }}
  .lead h4 {{ margin:0 0 .3rem; font-size:1rem; color:{INK}; line-height:1.35; }}
  .lead .meta {{ font-size:.75rem; color:#6b7671; letter-spacing:.04em; }}
  .lead .snip {{ font-size:.83rem; color:#4a544f; margin-top:.4rem; line-height:1.5; }}
  .chip {{ display:inline-block; padding:.1rem .5rem; border-radius:99px;
           font-size:.68rem; font-weight:700; letter-spacing:.06em; margin-right:.3rem; }}
  .kpi {{ background:#fff; border:1px solid #e2ded4; border-radius:3px;
          padding:.8rem 1rem; }}
  .kpi .n {{ font-size:1.8rem; font-weight:800; color:{INK}; line-height:1; }}
  .kpi .l {{ font-size:.68rem; text-transform:uppercase; letter-spacing:.11em;
             color:#6b7671; margin-top:.3rem; }}
  .guard {{ background:#fffbe9; border:1px solid #e8d9a0; border-radius:3px;
            padding:.7rem .9rem; font-size:.8rem; color:#5c4d1f; }}
  section[data-testid="stSidebar"] {{ background:#eeece5; }}
</style>""", unsafe_allow_html=True)

load_env()

# On Streamlit Cloud there is no .env; settings live in st.secrets. Copy them
# into the environment so every module keeps reading plain env vars.
# Check the file exists first: merely touching st.secrets without one makes
# Streamlit paint a red "No secrets files found" box on an otherwise fine app.
_SECRET_PATHS = [
    os.path.join(os.path.expanduser("~"), ".streamlit", "secrets.toml"),
    os.path.join(os.getcwd(), ".streamlit", "secrets.toml"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), ".streamlit",
                 "secrets.toml"),
    "/mount/src/.streamlit/secrets.toml",
]
if any(os.path.exists(_p) for _p in _SECRET_PATHS):
    try:
        for _key, _val in dict(st.secrets).items():
            if isinstance(_val, str) and _key not in os.environ:
                os.environ[_key] = _val
    except Exception:
        pass      # malformed or unreadable secrets — fall back to env vars


@st.cache_resource
def get_conn():
    return store.connect()


conn = get_conn()
cfg = load_config()

st.markdown("""<div class="masthead">
  <h1>🛟 Insurance Lead Radar</h1>
  <p>Public-post intent detection · Thai + English · human-in-the-loop outreach</p>
</div>""", unsafe_allow_html=True)

# ------------------------------------------------------------------ sidebar --
with st.sidebar:
    st.markdown("### Scan")
    picked = st.multiselect(
        "Platforms", list(sources.PLATFORMS),
        default=[p for p in cfg["platforms"] if p in sources.PLATFORMS],
        format_func=lambda k: sources.PLATFORMS[k]["label"])
    freshness = st.selectbox(
        "Recency", ["qdr:d", "qdr:w", "qdr:m", "qdr:y", ""],
        index=["qdr:d", "qdr:w", "qdr:m", "qdr:y", ""].index(cfg["freshness"]),
        format_func=lambda v: {"qdr:d": "Past 24 hours", "qdr:w": "Past week",
                               "qdr:m": "Past month", "qdr:y": "Past year",
                               "": "Any time"}[v])
    per_query = st.slider("Results per query", 3, 20, int(cfg["results_per_query"]))
    threshold = st.slider("Alert threshold", 0, 100, int(cfg["alert_threshold"]), 5,
                          help="Only posts scoring at or above this trigger an alert.")
    chans = st.multiselect("Alert channels", ["line", "telegram", "webhook", "desktop"],
                           default=cfg["alert_channels"])

    run_cfg = dict(cfg, platforms=picked, freshness=freshness,
                   results_per_query=per_query, alert_threshold=threshold,
                   alert_channels=chans)

    _status = getattr(sources, "backend_status", None) or \
              getattr(sources, "cli_status", None)
    if _status is None:      # radar/ is older than app.py — say so plainly
        cli_ok, cli_msg = False, ("radar/sources.py is out of date with app.py "
                                  "— redeploy with the whole radar/ folder.")
    else:
        cli_ok, cli_msg = _status()
    go = st.button("🔍 Scan now", type="primary", use_container_width=True,
                   disabled=not cli_ok)
    quiet = st.checkbox("Dry run (no alerts, no save)", value=False)
    if not cli_ok:
        st.error(cli_msg)

    st.divider()
    st.markdown("### Status")
    st.markdown(f"{'🟢' if cli_ok else '🔴'} search backend"
                + (f"  \n<span style='font-size:.72rem;color:#6b7671'>{cli_msg}"
                   f"</span>" if cli_ok else ""), unsafe_allow_html=True)
    for label, env_keys in [("LINE", ["LINE_CHANNEL_ACCESS_TOKEN"]),
                            ("Telegram", ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]),
                            ("Webhook", ["WEBHOOK_URL"])]:
        ready = all(os.getenv(k) for k in env_keys)
        st.markdown(f"{'🟢' if ready else '⚪️'} {label}"
                    f"{'' if ready else '  · not configured'}")
    if st.button("Send test alert", use_container_width=True):
        res = notify.dispatch([{
            "title": "ทดสอบระบบ: อยากทำประกันสุขภาพ แนะนำหน่อยครับ",
            "url": "https://pantip.com/topic/00000000", "platform": "pantip",
            "score": 88, "tier": "HOT", "products": ["health"]}], chans)
        for chan, out in res.items():
            (st.success if out == "sent" else st.warning)(f"{chan}: {out}")

# --------------------------------------------------------------------- scan --
if go:
    prog = st.progress(0.0, text="starting…")
    total = max(len(picked) * len(cfg["queries"]), 1)
    state = {"n": 0}

    def tick(msg: str) -> None:
        state["n"] += 1
        prog.progress(min(state["n"] / total, 1.0), text=msg)

    try:
        res = run_scan(conn, run_cfg, on_progress=tick, dry_run=quiet)
        prog.empty()
        st.success(
            f"Scanned **{res['scanned']}** posts · **{res['scored']}** matched intent · "
            f"**{res['new_leads']}** new · **{res['alerted']}** alerted")
        for chan, out in (res["channels"] or {}).items():
            (st.info if out == "sent" else st.warning)(f"alert · {chan}: {out}")
        if res["errors"]:
            with st.expander(f"{len(res['errors'])} source warning(s)"):
                for e in res["errors"]:
                    st.caption(e)
        if quiet and res["top"]:
            st.dataframe(pd.DataFrame([{
                "score": l["score"], "tier": l["tier"], "platform": l["platform"],
                "title": l["title"], "url": l["url"]} for l in res["top"]]),
                use_container_width=True, hide_index=True)
    except Exception as exc:
        prog.empty()
        st.error(f"Scan failed: {exc}")

tab_leads, tab_pulse, tab_rules = st.tabs(["🎯 Leads", "📊 Pulse", "🛡 Rules & limits"])

# -------------------------------------------------------------------- leads --
with tab_leads:
    c1, c2, c3 = st.columns([1.2, 1.5, 1.5])
    min_score = c1.slider("Min score", 0, 100, 40, 5, key="ms")
    statuses = c2.multiselect("Status", store.STATUSES, default=["new", "watching"])
    plats = c3.multiselect("Platform", list(sources.PLATFORMS), default=[])
    sort_new = c1.checkbox("Newest first", value=False)

    rows = store.fetch_leads(conn, min_score, statuses or None, plats or None)
    if sort_new:
        rows = sorted(rows, key=lambda r: r["first_seen"], reverse=True)

    k = st.columns(4)
    all_rows = store.fetch_leads(conn, 0, None, None, limit=5000)
    counts = {
        "leads tracked": len(all_rows),
        "hot (≥70)": sum(1 for r in all_rows if r["score"] >= 70),
        "new & untouched": sum(1 for r in all_rows if r["status"] == "new"),
        "contacted": sum(1 for r in all_rows if r["status"] in ("contacted", "qualified", "won")),
    }
    for col, (label, n) in zip(k, counts.items()):
        col.markdown(f'<div class="kpi"><div class="n">{n}</div>'
                     f'<div class="l">{label}</div></div>', unsafe_allow_html=True)
    st.write("")

    if not rows:
        st.info("No leads match these filters yet. Run a scan from the sidebar.")
    for r in rows[:120]:
        color = TIER_COLOR.get(r["tier"], "#888")
        products = ", ".join(json.loads(r["products"] or "[]")) or "unclassified"
        reasons = " · ".join(json.loads(r["reasons"] or "[]"))
        st.markdown(f"""<div class="lead" style="border-left-color:{color}">
          <h4>{r['title'] or '(no title)'}</h4>
          <div class="meta">
            <span class="chip" style="background:{color};color:#fff">{r['tier']} {r['score']}</span>
            <span class="chip" style="background:#eee;color:{INK}">{r['platform']}</span>
            <span class="chip" style="background:#eee;color:{INK}">{products}</span>
            first seen {r['first_seen'][:16].replace('T', ' ')} · status <b>{r['status']}</b>
          </div>
          <div class="snip">{(r['snippet'] or '')[:320]}</div>
          <div class="meta" style="margin-top:.45rem">{reasons}</div>
        </div>""", unsafe_allow_html=True)

        a, b, c = st.columns([2.2, 2.4, 5])
        a.link_button("Open post ↗", r["url"], use_container_width=True)
        new_status = b.selectbox(
            "status", store.STATUSES, index=store.STATUSES.index(r["status"]),
            key=f"s_{r['id']}", label_visibility="collapsed")
        if new_status != r["status"]:
            store.set_status(conn, r["id"], new_status)
            st.rerun()
        note = c.text_input("note", value=r["notes"] or "", key=f"n_{r['id']}",
                            placeholder="note to self (not sent anywhere)",
                            label_visibility="collapsed")
        if note != (r["notes"] or ""):
            store.set_status(conn, r["id"], new_status, note)

# -------------------------------------------------------------------- pulse --
with tab_pulse:
    rows = store.fetch_leads(conn, 0, None, None, limit=5000)
    if not rows:
        st.info("Nothing to chart yet — run a scan first.")
    else:
        df = pd.DataFrame([dict(r) for r in rows])
        df["products"] = df["products"].apply(lambda s: json.loads(s or "[]"))
        df["day"] = pd.to_datetime(df["first_seen"]).dt.date

        c1, c2 = st.columns(2)
        by_plat = df.groupby(["platform", "tier"]).size().reset_index(name="n")
        fig = px.bar(by_plat, x="platform", y="n", color="tier", barmode="stack",
                     color_discrete_map=TIER_COLOR, title="Leads by platform and tier")
        fig.update_layout(plot_bgcolor="#fff", paper_bgcolor=PAPER, height=330,
                          margin=dict(t=48, b=10, l=10, r=10))
        c1.plotly_chart(fig, use_container_width=True)

        exploded = df.explode("products").dropna(subset=["products"])
        if not exploded.empty:
            prod = exploded.groupby("products").size().reset_index(name="n") \
                           .sort_values("n")
            fig2 = px.bar(prod, x="n", y="products", orientation="h",
                          title="Demand by product line",
                          color_discrete_sequence=[ACCENT])
            fig2.update_layout(plot_bgcolor="#fff", paper_bgcolor=PAPER, height=330,
                               margin=dict(t=48, b=10, l=10, r=10), yaxis_title="")
            c2.plotly_chart(fig2, use_container_width=True)

        daily = df.groupby("day").size().reset_index(name="leads")
        fig3 = px.area(daily, x="day", y="leads", title="New leads discovered per day",
                       color_discrete_sequence=[ACCENT])
        fig3.update_layout(plot_bgcolor="#fff", paper_bgcolor=PAPER, height=280,
                           margin=dict(t=48, b=10, l=10, r=10))
        st.plotly_chart(fig3, use_container_width=True)

        funnel = df.groupby("status").size().reindex(store.STATUSES).fillna(0)
        st.markdown("##### Triage funnel")
        st.dataframe(funnel.rename("leads").to_frame().T, use_container_width=True)

        st.markdown("##### Scan history")
        runs = pd.DataFrame([dict(r) for r in store.fetch_runs(conn, 25)])
        if not runs.empty:
            st.dataframe(runs[["ts", "platforms", "scanned", "new_leads", "hot"]],
                         use_container_width=True, hide_index=True)

# --------------------------------------------------------------------- rules --
with tab_rules:
    st.markdown("""<div class="guard">
    <b>What this tool does and does not do.</b> It reads <i>publicly indexed</i>
    posts, scores them for insurance-buying intent, and tells you where they are.
    It does not log in, join private groups, send anyone a message, scrape
    profiles, or store contact details — phone numbers, emails and LINE IDs are
    stripped before anything is saved. Every outreach decision is yours, made by
    hand, on the platform's own terms of service. Under Thailand's PDPA, treat
    what you collect as personal data: keep it minimal, keep it for a reason you
    can state, and delete it when that reason is gone. Approaching someone to
    sell insurance also requires the licence the OIC demands for that product.
    </div>""", unsafe_allow_html=True)
    st.write("")

    left, right = st.columns(2)
    with left:
        st.markdown("##### Active queries")
        st.caption("Edit `config.yml` to change these permanently.")
        st.code("\n".join(cfg["queries"]), language=None)
    with right:
        st.markdown("##### Scoring weights")
        st.caption("Tune in `radar/keywords.py`.")
        st.markdown("""
| Signal | Max | Example |
|---|---|---|
| Buying intent | +45 | อยากทำประกันสุขภาพ, ตัวไหนดี |
| Life event | +30 | ท้อง, เพิ่งเริ่มทำงาน, ลดหย่อนภาษี |
| Product named | +20 | เหมาจ่าย, โรคร้ายแรง, ชั้น 1 |
| First-person question | +12 | เราควร…ไหมคะ |
| Urgency | +10 | ด่วน, ก่อนสิ้นปี |
| Unhappy with cover | +15 | เคลมไม่ผ่าน, อยากเปลี่ยนบริษัท |
| Agent ad / promo | −60 | สนใจทักแชท, โปรโมชั่น |
| Brochure wording | −50 | รับประกันโดย, คุ้มครองสูงสุด |
| Agent client story | −45 | ลูกค้าถามว่า, อยู่ใช่ไหม? |
| Broadcast voice | −40 | สำหรับใครที่กำลังมองหา |
| Career question | −40 | อยากเป็นตัวแทน, สอบใบอนุญาต |
| Publisher domain | −40 | tqm.co.th, aia.co.th |
| OCR'd from an image | −30 | ad creatives are pictures |
""")

    st.markdown("##### Try the scorer on any text")
    t = st.text_area("Paste a post", height=110,
                     value="เพิ่งรู้ว่าท้อง ตอนนี้ยังไม่มีประกันสุขภาพเลยค่ะ ควรทำประกันไหมคะ")
    if t.strip():
        from radar.scoring import score_post
        v = score_post(t, "", "")
        cA, cB = st.columns([1, 3])
        cA.metric("Score", f"{v['score']}/100", v["tier"])
        cB.write("**Why:** " + (" · ".join(v["reasons"]) or "no signals found"))
        cB.write("**Products:** " + (", ".join(v["products"]) or "unclassified"))
