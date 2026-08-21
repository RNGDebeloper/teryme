from pyrogram import filters
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot import Bot
from commands import build_help_text
from config import ADMINS
from database.ads_database import get_ad_settings


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📢 Broadcast", callback_data="menu_broadcast"), InlineKeyboardButton("⭐ Premium", callback_data="menu_premium")],
            [InlineKeyboardButton("🔐 Force-Sub", callback_data="menu_forcesub"), InlineKeyboardButton("💰 Ads", callback_data="menu_ads")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings"), InlineKeyboardButton("ℹ️ Help", callback_data="menu_help")],
        ]
    )


@Bot.on_message(filters.command("admin") & filters.private & filters.user(ADMINS))
async def admin_panel(client: Bot, message: Message):
    await message.reply_text("🏠 <b>Admin Menu</b>", reply_markup=main_menu())


@Bot.on_callback_query(filters.regex("^(menu_|about|close|settings_|premium_).*"))
async def cb_handler(client: Bot, query: CallbackQuery):
    data = query.data

    if data in {"menu_main", "close"}:
        if data == "close":
            await query.message.delete()
            return
        await query.message.edit_text("🏠 <b>Admin Menu</b>", reply_markup=main_menu())

    elif data == "menu_help":
        is_admin = query.from_user.id in ADMINS
        await query.message.edit_text(
            build_help_text(is_admin),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="menu_main")]]),
            disable_web_page_preview=True,
        )

    elif data == "menu_settings":
        if query.from_user.id not in ADMINS:
            await query.answer("Admins only", show_alert=True)
            return
        await query.message.edit_text(
            "⚙️ <b>Settings Menu</b>\nUse quick commands:\n"
            "/set_force_sub\n/set_start_pic\n/set_force_msg\n/set_force_pic",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="menu_main")]]),
        )

    elif data == "menu_forcesub":
        if query.from_user.id not in ADMINS:
            await query.answer("Admins only", show_alert=True)
            return
        await query.message.edit_text(
            "🔐 <b>Force-Subscribe Menu</b>\n\n"
            "Users must join this channel before using the bot.\n\n"
            "/set_force_sub — set the channel ID (bot must be admin there "
            "with 'Invite Users via Link' permission)\n"
            "/set_force_msg — customize the join prompt\n"
            "/set_force_pic — add an image to the join prompt\n\n"
            "Send /set_force_sub <code>0</code> to disable Force-Sub.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="menu_main")]]),
        )

    elif data == "menu_ads":
        if query.from_user.id not in ADMINS:
            await query.answer("Admins only", show_alert=True)
            return
        settings = await get_ad_settings()
        await query.message.edit_text(
            "💰 <b>Ads Menu</b>\n\n"
            f"Global Ads: <code>{'ON' if settings.get('ads_enabled') else 'OFF'}</code>\n"
            f"Mode: <code>{settings.get('mode')}</code>\n\n"
            "/enable_ads · /disable_ads\n"
            "/set_rewarded_popup zone_id\n"
            "/set_interstitial zone_id\n"
            "/set_ad_mode rewarded_popup|interstitial|both\n"
            "/ad_status — full status\n"
            "/ads_stats — conversion stats",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="menu_main")]]),
        )

    elif data == "menu_premium":
        await query.message.edit_text(
            "⭐ <b>Premium Menu</b>\nPremium users skip verification and get direct access.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("Buy Premium", callback_data="about")],
                    [InlineKeyboardButton("⬅️ Back", callback_data="menu_main")],
                ]
            ),
        )

    elif data == "menu_broadcast":
        if query.from_user.id not in ADMINS:
            await query.answer("Admins only", show_alert=True)
            return
        await query.message.edit_text(
            "📢 <b>Broadcast Menu</b>\nReply to any message with:\n/broadcast\n/pin_broadcast",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="menu_main")]]),
        )

    elif data == "about":
        await query.message.edit_text(
            text=
            "🔥 <b>Hey Buddy! Welcome to Premium 😎</b>\n\n"
            "Unlock the best experience with our <b>Premium Membership</b>.\n\n"

            "✨ <b>Premium Benefits</b>\n"
            "• 🚀 Direct download links (No Ads)\n"
            "• 📂 On-demand collections\n"
            "• 📝 1 custom request every day\n"
            "• 🎉 Special access to exclusive events\n"
            "• ⚡ Priority support\n\n"

            "📢 <b>Included Premium Channel</b>\n"
            "• <a href='https://t.me/Uchiha_Community'>Uchiha Community</a>\n"
            "• More exclusive channels coming soon...\n\n"

            "💎 <b>Pricing</b>\n"
            "• 1 Month — <b>$1</b>\n"
            "• 3 Months — <b>$5</b>\n"
            "• 6 Months — <b>$10</b>\n"
            "• 9 Months — <b>$15</b>\n"
            "• 12 Months — <b>$20</b>\n\n"

            "💳 <b>Payment Methods</b>\n"
            "• UPI\n"
            "• Crypto (DM <b>@Goxzi</b> for the wallet address)\n\n"

            "📩 <b>How to Subscribe?</b>\n"
            "1️⃣ Complete the payment.\n"
            "2️⃣ Send the payment screenshot to <b>@Goxzi</b>.\n"
            "3️⃣ Your Premium will be activated after verification.\n\n"

            "⚠️ <b>Limited-Time Offer!</b>\n"
            "Current prices are temporary and will increase soon.\n"
            "Premium seats are limited, so grab yours before they're gone!",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Back", callback_data="menu_main"), InlineKeyboardButton("🔒 Close", callback_data="close")]]
            ),
        )

    await query.answer()
