import asyncio
import random

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait, InputUserDeactivated, UserIsBlocked
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

try:
    from pyrogram.types import WebAppInfo
except Exception:  # pragma: no cover
    WebAppInfo = None

from bot import Bot
from commands import build_help_text
from config import ADMINS, CUSTOM_CAPTION, DISABLE_CHANNEL_BUTTON, PROTECT_CONTENT, START_MSG, WEB_BASE_URL
from database.ads_database import get_ads_stats, increment_files_unlocked
from database.bot_settings import get_bot_settings, update_bot_settings
from database.database import add_user, del_user, full_userbase, present_user
from database.premium_database import add_premium_user, is_premium_user, list_premium_users, remove_premium_user
from helper_func import clear_force_sub_cache, decode, get_force_sub_channel_id, get_force_sub_invite_link, get_messages, subscribed
from verification_system import create_access_token, is_unlock_ready, mark_token_used

# Keep only verified/public-safe IDs and always fallback if Telegram rejects it.
SAFE_EFFECT_IDS = [
    5046509860389126442,
    5104841245755180586,
    5046509860389126443,
    5107584321108051014
    
]


async def _safe_reply_with_effect(message: Message, text: str, **kwargs):
    effect_id = random.choice(SAFE_EFFECT_IDS)
    try:
        return await message.reply_text(text, message_effect_id=effect_id, **kwargs)
    except Exception:
        return await message.reply_text(text, **kwargs)


async def _deliver_files(client: Client, message: Message, ids):
    temp_msg = await message.reply("Please wait...")
    try:
        messages = await get_messages(client, ids)
    except Exception as err:
        await message.reply_text(f"Error: {err}")
        return

    await temp_msg.delete()

    for msg in messages:
        if bool(CUSTOM_CAPTION) and bool(msg.document):
            caption = CUSTOM_CAPTION.format(
                previouscaption="" if not msg.caption else msg.caption.html,
                filename=msg.document.file_name,
            )
        else:
            caption = "" if not msg.caption else msg.caption.html

        reply_markup = msg.reply_markup if DISABLE_CHANNEL_BUTTON else None

        try:
            await msg.copy(
                chat_id=message.from_user.id,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
                protect_content=PROTECT_CONTENT,
            )
            await asyncio.sleep(0.5)
        except FloodWait as e:
            await asyncio.sleep(e.x)
            await msg.copy(
                chat_id=message.from_user.id,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
                protect_content=PROTECT_CONTENT,
            )
        except Exception:
            continue


def _decode_ids(client: Client, encoded_string: str):
    argument = encoded_string.split("-")
    if len(argument) == 3:
        start = int(int(argument[1]) / abs(client.db_channel.id))
        end = int(int(argument[2]) / abs(client.db_channel.id))
        if start <= end:
            return list(range(start, end + 1))
        return list(range(start, end - 1, -1))

    if len(argument) == 2:
        return [int(int(argument[1]) / abs(client.db_channel.id))]

    return []


def _build_verify_keyboard(verify_url: str) -> InlineKeyboardMarkup:
    if WebAppInfo is None:
        raise RuntimeError("Pyrogram version does not support WebAppInfo. Please install pyrogram>=2.")
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Verify & Continue", web_app=WebAppInfo(url=verify_url))],
            [InlineKeyboardButton("😎 How to Open ?", url="https://t.me/hw2openlinks/3"), InlineKeyboardButton("✨ Buy Premium", callback_data="about")],
        ]
    )


async def _ask_and_save(client: Client, message: Message, key: str, prompt: str, caster=str):
    try:
        answer = await client.ask(chat_id=message.chat.id, text=prompt, timeout=120)
    except Exception as err:
        await message.reply_text(f"Error: {err}")
        return

    value = (answer.text or "").strip()
    if not value:
        await message.reply_text("Error: empty input is not allowed.")
        return

    try:
        parsed = caster(value)
    except Exception:
        await message.reply_text("Error: invalid input format.")
        return

    await update_bot_settings(client.me.id, {key: parsed})
    await message.reply_text(f"✅ Saved <code>{key}</code>.")


@Bot.on_message(filters.command("start") & filters.private & subscribed)
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id
    if not await present_user(user_id):
        try:
            await add_user(user_id)
        except Exception:
            pass

    settings = await get_bot_settings(client.me.id)

    text = message.text or ""
    if len(text) > 7:
        arg = text.split(" ", 1)[1]

        if arg.startswith("unlock_"):
            token = arg.split("_", 1)[1]
            token_data = await is_unlock_ready(token, user_id)
            if not token_data:
                await message.reply_text("❌ Verification invalid or expired. Please use the original file link again.")
                return

            try:
                decoded = await decode(token_data.get("base64_payload", ""))
                ids = _decode_ids(client, decoded)
            except Exception as err:
                await message.reply_text(f"Error: {err}")
                return

            await _deliver_files(client, message, ids)
            await mark_token_used(token)
            await increment_files_unlocked()
            return

        try:
            decoded = await decode(arg)
            ids = _decode_ids(client, decoded)
        except Exception as err:
            await message.reply_text(f"Error: {err}")
            return

        if await is_premium_user(user_id):
            await _deliver_files(client, message, ids)
            return

        token = await create_access_token(user_id, arg, bot_id=client.me.id)
        if not token:
            await message.reply_text("Verification service unavailable. Try again later.")
            return

        if not WEB_BASE_URL:
            await message.reply_text("⚠️ WEB_BASE_URL is not configured by admin. Unable to run ad verification.")
            return

        try:
            verify_url = f"{WEB_BASE_URL}/verify/{token}"
            kb = _build_verify_keyboard(verify_url)
            await _safe_reply_with_effect(
                message,
                "🛡️ <b>Complete Verification to Unlock Your File</b>\n\n"
                "To keep our service free, please complete a quick verification.\n\n"
                "📌 <b>Steps:</b>\n"
                "1️⃣ Click <b>Verify Now</b>.\n"
                "2️⃣ Complete the <b>Interstitial Ad</b>.\n"
                "3️⃣ Complete the <b>Rewarded Popup Ad</b>.\n"
                "4️⃣ Return here and your file will be unlocked automatically.\n\n"
                "🙏 Thank you for supporting the bot!",
                reply_markup=kb,
                disable_web_page_preview=True,
            )
        except Exception as e:
            await message.reply_text(f"Error: {e}")
        return

    # Restored previous /start layout.
    reply_markup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Join Community", url="https://t.me/Uchiha_Community"),
                InlineKeyboardButton("Join Backup", url="https://t.me/Uchiha_Hub"),
            ],
            [
                InlineKeyboardButton("Buy Premium", callback_data="about"),
                InlineKeyboardButton("Developer", url="https://t.me/Uchiha_Developer"),
            ],
        ]
    )

    start_pic = settings.get("start_pic")
    rendered = START_MSG.format(
        first=message.from_user.first_name,
        last=message.from_user.last_name,
        username=None if not message.from_user.username else "@" + message.from_user.username,
        mention=message.from_user.mention,
        id=message.from_user.id,
    )

    if start_pic:
        await message.reply_photo(start_pic, caption=rendered, reply_markup=reply_markup)
    else:
        await message.reply_text(
            text=rendered,
            reply_markup=reply_markup,
            disable_web_page_preview=True,
            quote=True,
        )


@Bot.on_message(filters.command("start") & filters.private & ~subscribed)
async def not_joined(client: Client, message: Message):
    settings = await get_bot_settings(client.me.id)
    force_sub_channel = await get_force_sub_channel_id(client)

    if not force_sub_channel:
        # Nothing enforced (or it was just disabled) — let the user retry.
        await message.reply_text("✅ You're all set. Please send /start again.")
        return

    invite_link = await get_force_sub_invite_link(client, force_sub_channel)

    buttons = []
    if invite_link:
        buttons.append([InlineKeyboardButton("🔔 Join Channel", url=invite_link)])

    try:
        retry_payload = message.command[1]
        retry_url = f"https://t.me/{client.username}?start={retry_payload}"
    except IndexError:
        retry_url = f"https://t.me/{client.username}?start=start"
    buttons.append([InlineKeyboardButton("🔄 Try Again", url=retry_url)])

    force_msg = settings.get("force_msg") or "Please join the required channel to continue."
    force_pic = settings.get("force_pic")
    rendered = force_msg.format(
        first=message.from_user.first_name,
        last=message.from_user.last_name,
        username=None if not message.from_user.username else "@" + message.from_user.username,
        mention=message.from_user.mention,
        id=message.from_user.id,
    )

    if not invite_link:
        rendered += (
            "\n\n⚠️ The join button couldn't be generated. Admin: please make sure "
            "the bot is an admin in the configured Force-Sub channel with "
            "'Invite Users via Link' permission."
        )

    if force_pic:
        await message.reply_photo(force_pic, caption=rendered, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await message.reply(
            text=rendered,
            reply_markup=InlineKeyboardMarkup(buttons),
            quote=True,
            disable_web_page_preview=True,
        )


@Bot.on_message(filters.command("help") & filters.private)
async def help_cmd(client: Bot, message: Message):
    is_admin = message.from_user.id in ADMINS
    await message.reply_text(build_help_text(is_admin), disable_web_page_preview=True)


@Bot.on_message(filters.command("users") & filters.private & filters.user(ADMINS))
async def get_users(client: Bot, message: Message):
    msg = await client.send_message(chat_id=message.chat.id, text="<b>Processing ...</b>")
    users = await full_userbase()
    await msg.edit(f"{len(users)} users are using this bot")


@Bot.on_message(filters.private & filters.command("broadcast") & filters.user(ADMINS))
async def send_text(client: Bot, message: Message):
    if not message.reply_to_message:
        await message.reply("<code>Use this command as a replay to any telegram message with out any spaces.</code>")
        return

    query = await full_userbase()
    broadcast_msg = message.reply_to_message
    total = successful = blocked = deleted = unsuccessful = 0

    pls_wait = await message.reply("<i>Broadcasting Message.. This will Take Some Time</i>")
    for chat_id in query:
        try:
            try:
                await broadcast_msg.copy(chat_id, message_effect_id=random.choice(SAFE_EFFECT_IDS))
            except Exception:
                await broadcast_msg.copy(chat_id)
            successful += 1
        except FloodWait as e:
            await asyncio.sleep(e.x)
            await broadcast_msg.copy(chat_id)
            successful += 1
        except UserIsBlocked:
            await del_user(chat_id)
            blocked += 1
        except InputUserDeactivated:
            await del_user(chat_id)
            deleted += 1
        except Exception:
            unsuccessful += 1
        total += 1

    status = f"""<b><u>Broadcast Completed</u>\n\nTotal Users: <code>{total}</code>\nSuccessful: <code>{successful}</code>\nBlocked Users: <code>{blocked}</code>\nDeleted Accounts: <code>{deleted}</code>\nUnsuccessful: <code>{unsuccessful}</code></b>"""

    await pls_wait.edit(status)


@Bot.on_message(filters.private & filters.command("pin_broadcast") & filters.user(ADMINS))
async def pin_broadcast(client: Bot, message: Message):
    if not message.reply_to_message:
        await message.reply_text("❌ Reply to a message to broadcast")
        return

    broadcast_msg = message.reply_to_message
    users = await full_userbase()
    success_count = 0
    pin_success_count = 0
    fail_count = 0

    progress = await message.reply_text("<i>📢 Starting pin broadcast...</i>")

    for chat_id in users:
        try:
            sent_msg = await client.copy_message(
                chat_id=chat_id,
                from_chat_id=broadcast_msg.chat.id,
                message_id=broadcast_msg.id,
            )
            success_count += 1
            try:
                await client.pin_chat_message(chat_id, sent_msg.id, disable_notification=True)
                pin_success_count += 1
            except Exception:
                pass
        except FloodWait as e:
            await asyncio.sleep(e.x)
            try:
                sent_msg = await client.copy_message(
                    chat_id=chat_id,
                    from_chat_id=broadcast_msg.chat.id,
                    message_id=broadcast_msg.id,
                )
                success_count += 1
                try:
                    await client.pin_chat_message(chat_id, sent_msg.id, disable_notification=True)
                    pin_success_count += 1
                except Exception:
                    pass
            except Exception:
                fail_count += 1
        except (UserIsBlocked, InputUserDeactivated):
            await del_user(chat_id)
            fail_count += 1
        except Exception:
            fail_count += 1

    await progress.edit_text(
        "✅ Broadcast Done!\n"
        f"Sent: <code>{success_count}</code>\n"
        f"Pinned: <code>{pin_success_count}</code>\n"
        f"Failed: <code>{fail_count}</code>"
    )


@Bot.on_message(filters.private & filters.command("ads_stats") & filters.user(ADMINS))
async def ads_stats_cmd(client: Bot, message: Message):
    stats = await get_ads_stats()
    total_users = len(await full_userbase())
    completed_ads = int(stats.get("completed_ads", 0))
    conversion = (completed_ads / total_users * 100) if total_users else 0
    await message.reply_text(
        "📊 <b>Ads Stats:</b>\n\n"
        f"👥 Total Users: <code>{total_users}</code>\n"
        f"✅ Completed Ads: <code>{completed_ads}</code>\n"
        f"💰 Conversion Rate: <code>{conversion:.2f}%</code>\n\n"
        "🌍 <b>Tier Breakdown:</b>\n"
        f"Tier 1: <code>{int(stats.get('tier_1_users', 0))}</code> users\n"
        f"Tier 2: <code>{int(stats.get('tier_2_users', 0))}</code> users\n"
        f"Tier 3: <code>{int(stats.get('tier_3_users', 0))}</code> users\n\n"
        f"📁 Total Files Unlocked: <code>{int(stats.get('files_unlocked', 0))}</code>"
    )


@Bot.on_message(filters.private & filters.command("add_premium") & filters.user(ADMINS))
async def add_premium_cmd(client: Bot, message: Message):
    if len(message.command) < 2 or not message.command[1].isdigit():
        await message.reply_text("Usage: /add_premium user_id")
        return
    user_id = int(message.command[1])
    done = await add_premium_user(user_id, message.from_user.id)
    await message.reply_text("✅ Premium added." if done else "Error: failed to add premium user.")


@Bot.on_message(filters.private & filters.command("remove_premium") & filters.user(ADMINS))
async def remove_premium_cmd(client: Bot, message: Message):
    if len(message.command) < 2 or not message.command[1].isdigit():
        await message.reply_text("Usage: /remove_premium user_id")
        return
    user_id = int(message.command[1])
    done = await remove_premium_user(user_id)
    await message.reply_text("✅ Premium removed." if done else "Error: failed to remove premium user.")


@Bot.on_message(filters.private & filters.command("premium_list") & filters.user(ADMINS))
async def premium_list_cmd(client: Bot, message: Message):
    users = await list_premium_users()
    if not users:
        await message.reply_text("No premium users found.")
        return
    await message.reply_text("⭐ Premium users:\n" + "\n".join([f"<code>{u}</code>" for u in users[:400]]))


@Bot.on_message(filters.private & filters.command("set_force_sub") & filters.user(ADMINS))
async def set_force_sub(client: Bot, message: Message):
    await _ask_and_save(client, message, "force_sub_channel", "Send channel ID (e.g. -1001234567890)", int)
    clear_force_sub_cache(client)


@Bot.on_message(filters.private & filters.command("set_start_pic") & filters.user(ADMINS))
async def set_start_pic(client: Bot, message: Message):
    await _ask_and_save(client, message, "start_pic", "Send start image URL")


@Bot.on_message(filters.private & filters.command("set_force_msg") & filters.user(ADMINS))
async def set_force_msg(client: Bot, message: Message):
    await _ask_and_save(client, message, "force_msg", "Send custom force subscribe message")


@Bot.on_message(filters.private & filters.command("set_force_pic") & filters.user(ADMINS))
async def set_force_pic(client: Bot, message: Message):
    await _ask_and_save(client, message, "force_pic", "Send force image URL")
