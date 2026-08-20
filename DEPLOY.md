# Deploying to Streamlit Community Cloud

The dashboard runs on Streamlit Cloud, but **the firecrawl CLI cannot**. It is a
Node binary; Streamlit Cloud installs Python packages from `requirements.txt`
and nothing else. The radar therefore has two search transports and picks one
automatically:

| Situation | Transport used |
|---|---|
| `FIRECRAWL_API_KEY` is set | Firecrawl REST API, authenticated |
| No key, CLI on the machine | the local CLI (your authenticated plan) |
| No key, no CLI — i.e. the cloud | Firecrawl REST API, unauthenticated + usage-limited |

So a fresh deploy works with no configuration at all, just with lower limits.

## 1. Push the whole folder

The `AttributeError: module 'radar.sources' has no attribute 'cli_status'` you
saw is a **partial upload**: a new `app.py` next to an old `radar/sources.py`.
`app.py` and `radar/` are one unit — always deploy them together.

```
app.py
requirements.txt
config.yml
radar/__init__.py
radar/config.py
radar/keywords.py
radar/notify.py
radar/pipeline.py
radar/scoring.py
radar/sources.py
radar/store.py
```

Do **not** commit `.env` or `data/leads.db`.

## 2. Point the app at the right file

In the Streamlit Cloud app settings, set **Main file path** to `app.py` (or
`insurance-lead-radar/app.py` if the project sits in a subfolder of your repo).

## 3. Add your secrets

Streamlit Cloud has no `.env`. Open **Settings → Secrets** and paste TOML —
`app.py` copies these into the environment on startup, so every module keeps
reading plain env vars:

```toml
FIRECRAWL_API_KEY = "fc-…"
LINE_CHANNEL_ACCESS_TOKEN = "…"
LINE_TO = ""
TELEGRAM_BOT_TOKEN = "…"
TELEGRAM_CHAT_ID = "…"
```

Everything is optional. Skip the Firecrawl key to run usage-limited; skip the
alert tokens to use the dashboard without notifications.

## 4. Things that behave differently in the cloud

- **The database resets.** `data/leads.db` lives on ephemeral disk, so leads and
  your triage statuses disappear whenever the app reboots. For anything you care
  about keeping, run the radar locally, or point `radar/store.py` at a hosted
  Postgres.
- **Desktop alerts do not work** — `desktop` is macOS-only. In the cloud use
  `line`, `telegram`, or `webhook`.
- **Nothing runs while the tab is closed.** Streamlit Cloud sleeps idle apps, so
  a hosted dashboard is for triage, not for catching leads around the clock. Use
  `python run_radar.py --loop 60` on a machine that stays awake for that.
- **Your app may be publicly reachable.** This one displays scraped posts and
  your private notes, so set the app to private, or restrict access by email, in
  the Streamlit Cloud sharing settings.

## Verifying a deploy

The sidebar shows a **search backend** line. Green with "Firecrawl API" means
the cloud path is live. If it is red, the message names the fix.
