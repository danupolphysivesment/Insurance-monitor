# 🛟 Insurance Lead Radar

Finds **public social posts from people who need insurance** — Thai and English —
scores them for buying intent, and pings you on **LINE** (or Telegram / Discord /
macOS) when a good one appears. Triage them in a Streamlit dashboard.

Built for the Thai market: Pantip, X, public Facebook posts, Threads, Reddit.

```bash
cd insurance-lead-radar
pip install -r requirements.txt
cp .env.example .env          # add your LINE or Telegram token
python run_radar.py --once    # one scan from the terminal
streamlit run app.py --server.port 8580   # dashboard
```

## What it does — and deliberately does NOT do

| ✅ Does | ❌ Does not |
|--------|-------------|
| Read **publicly indexed** posts via Firecrawl search | Log in, or enter private groups |
| Score them for insurance-buying intent | Message, comment on, or DM anyone |
| Alert you with a link to the post | Store phone numbers, emails or LINE IDs |
| Let you triage and take notes by hand | Auto-reply, auto-follow, or bulk-outreach |

The redaction step in `radar/scoring.py` strips phone numbers, emails and LINE IDs
*before* anything is written to disk or sent to a chat app. That is deliberate: to
triage a lead you need the post, not the person's contact details.

**Before you use it commercially:** Thailand's **PDPA** treats what you collect
here as personal data — keep it minimal, have a stated purpose, delete it when
that purpose ends. Selling insurance requires the **OIC** licence for the product
you are pitching, and every platform's terms govern how you may approach someone
who posted there. This tool finds the conversation; joining it is your call and
your responsibility.

## How a post gets scored

`radar/keywords.py` holds the entire signal taxonomy — edit it, no logic changes
needed. `radar/scoring.py` combines the signals into 0–100:

| Signal | Max | Example |
|---|---|---|
| Buying intent | +45 | `อยากทำประกันสุขภาพ`, `เจ้าไหนดี`, `looking for health insurance` |
| Life event | +30 | `ท้อง`, `เพิ่งเริ่มทำงาน`, `ลาออกจากงาน`, `ลดหย่อนภาษี` |
| Product named | +20 | `เหมาจ่าย`, `โรคร้ายแรง`, `ประกันชั้น 1`, `ยูนิตลิงค์` |
| Unhappy with current cover | +15 | `เคลมไม่ผ่าน`, `อยากเปลี่ยนบริษัทประกัน` |
| First-person question | +12 | `เราควรทำประกันไหมคะ` |
| Urgency | +10 | `ด่วน`, `ก่อนสิ้นปี` |
| Agent ad / promo | −60 | `สนใจทักแชท`, `โปรโมชั่นพิเศษ` |
| Brochure / ad-creative wording | −50 | `รับประกันโดย`, `คุ้มครองสูงสุด`, `เริ่มต้นเพียงวันละ` |
| Agent retelling a client story | −45 | `ลูกค้าถามว่า`, `กำลังมองหาประกันอยู่ใช่ไหม?` |
| Broadcast voice | −40 | `สำหรับใครที่กำลังมองหา`, `ขอแชร์ประสบการณ์` |
| Career question about insurance | −40 | `อยากเป็นตัวแทน`, `สอบใบอนุญาต` |
| Publisher / insurer domain | −40 | `tqm.co.th`, `aia.co.th`, news sites |
| Text OCR'd from an image | −30 | ad creatives arrive as pictures; people type |

Tiers: **HOT ≥ 70 · WARM 45–69 · COOL < 45**. Default alert threshold is 50.

The negative weights are the important half. Search for "อยากทำประกันสุขภาพ" and
most of what comes back is agents advertising and insurers' content marketing —
the filters exist so your alert list stays *people with a need*.

What the sources are actually like, from the first live sweeps:

- **Facebook groups** are the richest vein — people post plainly there
  (*"ลูกเพิ่งหายป่วยจาก RSV แต่อยากทำประกันสุขภาพ แนะนำหน่อยค่ะ"*) — but the same
  groups are thick with agents, so most of the negative rules exist because of
  Facebook.
- **Pantip** gives the most considered posts, including B2B ones (an HR asking
  for group cover for 20 staff). Lower volume, higher quality.
- **X** is fast but dominated by finance-content accounts.
- **Reddit** is mostly expats, in English — worth it for travel and expat health.

Posts are also filtered by URL shape: an `x.com` hit must be a `/status/`, a
Pantip hit a `/topic/`, a Reddit hit a `/comments/`. Profile and tag pages are
dropped, as are known finance-content accounts (`radar/keywords.py`,
`BLOCKED_HANDLES`).

## Alerts

Configure in `.env`. Anything you leave blank is skipped silently.

### LINE (recommended)

LINE Notify was **shut down on 31 March 2025**, so this uses the **Messaging API**:

1. Open <https://developers.line.biz/console/> and create a **Messaging API**
   channel — this also creates a free LINE Official Account.
2. **Messaging API** tab → issue a long-lived **Channel access token** →
   `LINE_CHANNEL_ACCESS_TOKEN`.
3. Scan the OA's QR code on your phone so you're a friend of it.
4. Leave `LINE_TO` blank to broadcast to yourself, or paste your `userId` from
   the **Basic settings** tab.

You get one tappable Flex card carrying every lead in the batch — score, platform
and product line each. It is one message on purpose: a free LINE Official Account
only allows about **200 pushes per month**, so the radar never sends two. If you
expect more alert volume than that, use Telegram (unlimited and free) as the
primary channel and keep LINE for HOT leads only — set `alert_channels: [telegram]`
in `config.yml` and run a second high-threshold job for LINE.

### Telegram (fastest to set up)

Message `@BotFather` → `/newbot` → copy the token into `TELEGRAM_BOT_TOKEN`.
Message your bot once, then read your chat id from
`https://api.telegram.org/bot<TOKEN>/getUpdates` → `TELEGRAM_CHAT_ID`.

### Discord / Slack / n8n

Paste an incoming webhook URL into `WEBHOOK_URL`. macOS banners need no setup.

Verify any of them with:

```bash
python run_radar.py --test-alert
```

## Rate limits

Searches run in a small thread pool (`workers: 3` in `config.yml`). Push it
higher and Firecrawl starts returning **429**, which quietly costs you whole
platforms — an early run at 6 workers lost 31 of 48 queries that way. Rate-limited
searches are retried with backoff (4s → 9s, jittered) and each search is capped
at 45s, so a stuck query is reported in the scan summary rather than freezing the
progress bar for minutes. If you see
a lot of 429 warnings, drop `workers` to 2 or shorten your query list; a full
sweep of 4 platforms × 15 queries takes roughly a minute at the default.

## Running it continuously

```bash
python run_radar.py --loop 60
```

Or hand it to launchd / cron:

```bash
0 */2 * * * cd /path/to/insurance-lead-radar && /usr/bin/python3 run_radar.py --once >> data/radar.log 2>&1
```

Every two hours is plenty — these posts are not time-critical the way a sneaker
drop is, and search indexes take a while to pick new posts up anyway.

## CLI

```
python run_radar.py --once                  one scan, alert, exit
python run_radar.py --loop 30               scan every 30 minutes
python run_radar.py --dry-run               score and print, store nothing
python run_radar.py --test-alert            check your alert wiring
python run_radar.py --platforms pantip,x    override sources
python run_radar.py --threshold 65          override alert threshold
```

## Dashboard

`streamlit run app.py --server.port 8580`

- **🎯 Leads** — scored cards with the reason for each score, a status pipeline
  (new → watching → contacted → qualified → won / dismissed) and private notes.
- **📊 Pulse** — leads by platform and tier, demand by product line, discovery
  over time, triage funnel, scan history.
- **🛡 Rules & limits** — the guardrails, the active queries, the weight table,
  and a live scorer you can paste any text into.

## Files

```
config.yml            queries, platforms, thresholds, channels
run_radar.py          CLI runner (--once / --loop / --dry-run / --test-alert)
app.py                Streamlit dashboard (port 8580)
radar/keywords.py     the whole Thai/English signal taxonomy — tune here first
radar/scoring.py      0-100 intent scoring + contact-detail redaction
radar/sources.py      Firecrawl collectors, URL-shape filters, query packs
radar/notify.py       LINE / Telegram / webhook / macOS dispatch
radar/store.py        SQLite: leads, statuses, notes, scan history
radar/pipeline.py     collect → score → dedupe → store → alert
data/leads.db         created on first run
```

Requires the **firecrawl** CLI (already installed and authenticated on this
machine). The radar looks for it on PATH and then in the usual install
directories (`/opt/homebrew/bin`, `/usr/local/bin`, `~/.local/bin`, npm/volta/bun
bins). That fallback matters: a Streamlit app launched from a GUI does not
inherit your shell's PATH, so `which firecrawl` succeeding in a terminal does not
mean the dashboard can see it. If it still cannot be found, set `FIRECRAWL_BIN`
in `.env` to the full path and the sidebar will go green.

## Tuning it for your book of business

1. Run `--dry-run` for a few days and watch what scores 40–60.
2. Move phrases you keep seeing into `INTENT` or `NEGATIVE` in `keywords.py`.
3. Add queries to `config.yml` for the products you actually sell — group health,
   key-man cover, and unit-linked all have their own vocabulary.
4. Raise the threshold once your precision is good; start low and read everything.
