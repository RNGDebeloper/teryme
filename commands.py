"""Central registry of every bot command.

This is the single source of truth for:
- The catch-all handlers (`useless.py`, `channel_post.py`) that must ignore
  real commands instead of swallowing them.
- The in-bot /help and admin menu text (`plugins/cbb.py`, `plugins/start.py`).
- Telegram's native "/" command list (set in `bot.py`).

Add a new command here once and every one of the above stays in sync
automatically — no more hunting through multiple files to wire up a new
command.
"""

from typing import List, Tuple

# Each group: (section title, [(command, description, admin_only), ...])
COMMAND_GROUPS: List[Tuple[str, List[Tuple[str, str, bool]]]] = [
    ("👤 General", [
        ("start", "Open the bot / unlock a shared file link", False),
        ("help", "Show this help message", False),
    ]),
    ("📊 Stats", [
        ("users", "Show total bot users", True),
        ("stats", "Show bot uptime", True),
        ("ads_stats", "Show ad verification & conversion stats", True),
    ]),
    ("🔗 File Links", [
        ("genlink", "Generate a share link for one DB post", True),
        ("batch", "Generate a share link for a range of DB posts", True),
    ]),
    ("📢 Broadcast", [
        ("broadcast", "Send a message to all users (reply to a message)", True),
        ("pin_broadcast", "Send & pin a message to all users (reply to a message)", True),
    ]),
    ("⭐ Premium", [
        ("add_premium", "Grant premium — /add_premium user_id", True),
        ("remove_premium", "Revoke premium — /remove_premium user_id", True),
        ("premium_list", "List premium users", True),
    ]),
    ("🔐 Force-Subscribe", [
        ("set_force_sub", "Set the force-subscribe channel ID", True),
        ("set_force_msg", "Set the force-subscribe message", True),
        ("set_force_pic", "Set the force-subscribe image URL", True),
        ("set_start_pic", "Set the /start image URL", True),
    ]),
    ("💰 Ads", [
        ("enable_ads", "Enable ad verification globally", True),
        ("disable_ads", "Disable ad verification globally", True),
        ("set_rewarded_popup", "Set the Rewarded Popup zone — /set_rewarded_popup zone_id", True),
        ("set_interstitial", "Set the Interstitial zone/script — /set_interstitial zone_id", True),
        ("set_ad_mode", "Set ad mode — /set_ad_mode rewarded_popup|interstitial|both", True),
        ("ad_status", "Show current ad configuration", True),
    ]),
    ("🛠️ Admin Panel", [
        ("admin", "Open the interactive admin menu", True),
    ]),
]

USER_COMMANDS: List[str] = [
    cmd for _, cmds in COMMAND_GROUPS for cmd, _, admin_only in cmds if not admin_only
]

ADMIN_COMMANDS: List[str] = [
    cmd for _, cmds in COMMAND_GROUPS for cmd, _, admin_only in cmds if admin_only
]

ALL_COMMANDS: List[str] = USER_COMMANDS + ADMIN_COMMANDS


def build_help_text(is_admin: bool) -> str:
    """Render the /help text. Admins see every group, everyone else sees
    only the general/public commands."""
    lines = ["ℹ️ <b>Available Commands</b>\n"]
    for title, cmds in COMMAND_GROUPS:
        visible = [c for c in cmds if is_admin or not c[2]]
        if not visible:
            continue
        lines.append(f"<b>{title}</b>")
        for cmd, desc, _ in visible:
            lines.append(f"/{cmd} — {desc}")
        lines.append("")
    return "\n".join(lines).strip()
