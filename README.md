# 🚀 Force4You Premium File Sharing Bot

A professional Pyrogram-based Telegram bot for secure file sharing, monetized verification, premium bypass, force-subscribe control, and scalable admin workflows.

---

## Bot Overview

Force4You is designed for Telegram communities that need:
- Fast file-link generation from a private DB channel
- Batch sharing links for collections
- Ad/verification flow for non-premium users
- Direct premium delivery (verification bypass)
- Broadcast communication tools
- Per-bot settings management for multi-bot environments

---

## Key Features

- ✅ **Modern `/start` Home UI** with menu buttons and dynamic bot stats
- ✅ **Direct Link Generation** (`/genlink`) and **Batch Link Generation** (`/batch`)
- ✅ **Clone/Multi-bot compatible settings model** (`bot_id` based config storage)
- ✅ **Centralized Ads System** (rewarded popup/interstitial toggle + mode)
- ✅ **Premium System** (add/remove/list + verification bypass)
- ✅ **Force Subscribe System** with a dynamically-resolved join link (works for public and private channels, auto-generates an invite link, caches it, and self-heals if the channel is changed via `/set_force_sub`)
- ✅ **Broadcast System** including pinned broadcast mode
- ✅ **In-bot Admin Panel** (`/admin`) — every setting reachable from inline buttons, no need to remember commands
- ✅ **Self-updating `/help`** and native Telegram "/" command menu — every command is discoverable from inside the chat, with admin-only commands hidden from regular users
- ✅ **Telegram Message Effects** with safe fallback handling
- ✅ **Error-safe command handling** with validation-first design

---

## Commands

Run `/help` inside the bot at any time for the full, always up-to-date list
(it's generated from `commands.py`, so it can never drift out of sync with
what's actually registered). Or open `/admin` for a button-driven menu.

### User Commands
- `/start` — open bot home and process shared file links.
- `/help` — show the command list (admins see admin commands too).

### Admin Commands
- `/admin` — open the interactive admin menu (Broadcast, Premium, Force-Sub, Ads, Settings, Help).
- `/genlink` — generate link for one DB post.
- `/batch` — generate one link for multiple DB posts.
- `/users` — total bot users.
- `/stats` — bot uptime.

### Broadcast Commands
- `/broadcast` *(reply to message)* — send to all users.
- `/pin_broadcast` *(reply to message)* — send and pin in all user chats.

### Premium Commands
- `/add_premium user_id` — grant premium.
- `/remove_premium user_id` — revoke premium.
- `/premium_list` — show premium users.

### Force-Subscribe Commands
- `/set_force_sub` — set the force-subscribe channel ID (send `0` to disable it).
- `/set_start_pic` — set start image URL.
- `/set_force_msg` — set force-subscribe text (supports `{first}`, `{last}`, `{username}`, `{mention}`, `{id}`).
- `/set_force_pic` — set force-subscribe image URL.

### Ads Commands
- `/enable_ads`, `/disable_ads`
- `/set_rewarded_popup <zone-id>`
- `/set_interstitial <zone/script>`
- `/set_ad_mode rewarded_popup|interstitial|both`
- `/ad_status` — full ad configuration status.
- `/ads_stats` — conversion/tier stats.

---

## Force-Subscribe: how the join link is resolved

Previously the "join channel" button on the force-sub prompt was hardcoded
to unrelated placeholder channels and a stale, startup-only invite link —
so it could show the wrong channel, or fail to show any button at all if
the bot hadn't cached one. This has been fixed:

1. `helper_func.get_force_sub_channel_id()` resolves the channel to enforce
   — the per-bot value set via `/set_force_sub` (stored in MongoDB) takes
   priority, falling back to the `FORCE_SUB_CHANNEL` env var.
2. `helper_func.get_force_sub_invite_link()` fetches a fresh, correct join
   link for that exact channel: a `t.me/<username>` link for public
   channels, or a generated invite link for private ones. It's cached on
   the running client so repeat `/start` attempts don't re-hit the API.
3. Running `/set_force_sub` clears that cache immediately, so the very next
   blocked user sees the newly-configured channel, not a stale one.
4. If the bot isn't an admin in the target channel (so it can't verify
   membership or generate a link), the flow now **fails open with a
   logged warning** instead of silently breaking the whole `/start` flow —
   users aren't permanently locked out by a misconfiguration, and the
   error is visible in your logs.

**For Force-Sub to work**, the bot must be an admin in the configured
channel with the *"Invite Users via Link"* permission (and *"Add Members"*
for private channels).

---

## Environment Variables

Required:
- `TG_BOT_TOKEN` — bot token from BotFather
- `APP_ID` — Telegram API ID
- `API_HASH` — Telegram API hash
- `OWNER_ID` — owner user ID
- `CHANNEL_ID` — DB/storage channel ID (`-100...`)
- `DATABASE_URL` (or `DB_URI`) — Mongo URI
- `DATABASE_NAME` — Mongo database name

Common Optional:
- `ADMINS` — space-separated admin IDs
- `FORCE_SUB_CHANNEL` — default force-sub channel ID (overridable at runtime via `/set_force_sub`)
- `START_MESSAGE` — custom start message template
- `FORCE_SUB_MESSAGE` — custom force-sub message template
- `START_PIC` — default start image URL
- `CUSTOM_CAPTION` — custom caption template
- `WEB_BASE_URL` — public URL for verification web routes
- `PROTECT_CONTENT` — `True`/`False`
- `DISABLE_CHANNEL_BUTTON` — `True`/`False`
- `BOT_STATS_TEXT`
- `USER_REPLY_TEXT`
- `LOG_CHANNEL` (optional if used in your infra)
- `DUMP_CHANNEL_ID` (optional, if your deployment uses it)

---

## Database Models

### Bot-specific config
```json
{
  "_id": "bot:<bot_id>",
  "force_sub_channel": -1001234567890,
  "start_pic": "https://...",
  "force_msg": "custom text",
  "force_pic": "https://..."
}
```

### Premium users
```json
{
  "_id": 123456789,
  "added_by": 111111111,
  "updated_at": "UTC datetime"
}
```

---

## Deployment Guide

### 1) Clone and install
```bash
git clone <your-repo-url>
cd Force4You
pip install -r requirements.txt
```

### 2) Export environment variables
Set all required values (`TG_BOT_TOKEN`, `APP_ID`, `API_HASH`, `OWNER_ID`, `CHANNEL_ID`, `DATABASE_URL`, `DATABASE_NAME`).

### 3) Run bot
```bash
python main.py
```

### Platform options
- Railway
- VPS (systemd/supervisor)
- Docker-based hosts

---

## Notes

- Ads/verification are served via web routes and redirect/miniapp flow.
- Premium users bypass verification and receive content directly.
- Force-sub and start visuals/messages are editable at runtime via commands — no restart needed.
- `commands.py` is the single source of truth for every command: it drives the catch-all
  filters (so admin commands are never swallowed by the "not a file" auto-reply), the
  `/help` text, and the native Telegram command menu. Add a command there once and it's
  wired up everywhere.
- For stable production, ensure the bot is admin in both the DB channel and the force-sub channel.

---

## License

GPL-3.0 (same as repository license).
