#(©)Codexbotz

import base64
import re
import asyncio
from typing import Optional
from pyrogram import filters
from pyrogram.enums import ChatMemberStatus
from config import FORCE_SUB_CHANNEL, ADMINS
from database.bot_settings import get_force_sub_channel
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant
from pyrogram.errors import FloodWait


async def get_force_sub_channel_id(client) -> Optional[int]:
    """Resolve the channel currently enforced for force-subscribe.

    Prefers the per-bot value saved via /set_force_sub (stored in DB), and
    falls back to the FORCE_SUB_CHANNEL env var. Returns None if neither is
    configured, meaning force-sub is off.
    """
    force_sub_channel = FORCE_SUB_CHANNEL or None
    try:
        if getattr(client, "me", None):
            dynamic_channel = await get_force_sub_channel(client.me.id)
            if dynamic_channel is not None:
                force_sub_channel = dynamic_channel
    except Exception:
        pass
    return force_sub_channel or None


async def get_force_sub_invite_link(client, channel_id: int) -> Optional[str]:
    """Return a joinable link for the force-sub channel, generating and
    caching one on the client if needed. Works for public channels
    (t.me/username) and private ones (invite link)."""
    if not channel_id:
        return None

    cache = getattr(client, "_invite_link_cache", None)
    if cache is None:
        cache = {}
        client._invite_link_cache = cache
    if channel_id in cache:
        return cache[channel_id]

    link = None
    try:
        chat = await client.get_chat(channel_id)
        if chat.username:
            link = f"https://t.me/{chat.username}"
        elif chat.invite_link:
            link = chat.invite_link
        else:
            link = await client.export_chat_invite_link(channel_id)
    except Exception as e:
        try:
            client.LOGGER(__name__).warning(
                f"Force-Sub: couldn't get an invite link for channel {channel_id}: {e}. "
                "Make sure the bot is an admin there with 'Invite Users via Link' permission."
            )
        except Exception:
            pass
        return None

    if link:
        cache[channel_id] = link
    return link


def clear_force_sub_cache(client, channel_id: Optional[int] = None) -> None:
    """Drop cached invite link(s) so a freshly-set channel is resolved again."""
    cache = getattr(client, "_invite_link_cache", None)
    if not cache:
        return
    if channel_id is None:
        cache.clear()
    else:
        cache.pop(channel_id, None)


async def is_subscribed(filter, client, update):
    user_id = update.from_user.id
    if user_id in ADMINS:
        return True

    force_sub_channel = await get_force_sub_channel_id(client)
    if not force_sub_channel:
        return True

    try:
        member = await client.get_chat_member(chat_id=force_sub_channel, user_id=user_id)
    except UserNotParticipant:
        return False
    except Exception as e:
        # If the bot can't check membership (wrong ID, bot not in channel,
        # not an admin there, etc.) fail-open instead of locking every user
        # out of the bot with no feedback. Log it so the admin can fix it.
        try:
            client.LOGGER(__name__).warning(
                f"Force-Sub: membership check failed for channel {force_sub_channel}: {e}"
            )
        except Exception:
            pass
        return True

    return member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.MEMBER]

async def encode(string):
    string_bytes = string.encode("ascii")
    base64_bytes = base64.urlsafe_b64encode(string_bytes)
    base64_string = (base64_bytes.decode("ascii")).strip("=")
    return base64_string

async def decode(base64_string):
    base64_string = base64_string.strip("=") # links generated before this commit will be having = sign, hence striping them to handle padding errors.
    base64_bytes = (base64_string + "=" * (-len(base64_string) % 4)).encode("ascii")
    string_bytes = base64.urlsafe_b64decode(base64_bytes) 
    string = string_bytes.decode("ascii")
    return string

async def get_messages(client, message_ids):
    messages = []
    total_messages = 0
    while total_messages != len(message_ids):
        temb_ids = message_ids[total_messages:total_messages+200]
        try:
            msgs = await client.get_messages(
                chat_id=client.db_channel.id,
                message_ids=temb_ids
            )
        except FloodWait as e:
            await asyncio.sleep(e.x)
            msgs = await client.get_messages(
                chat_id=client.db_channel.id,
                message_ids=temb_ids
            )
        except:
            pass
        total_messages += len(temb_ids)
        messages.extend(msgs)
    return messages

async def get_message_id(client, message):
    if message.forward_from_chat:
        if message.forward_from_chat.id == client.db_channel.id:
            return message.forward_from_message_id
        else:
            return 0
    elif message.forward_sender_name:
        return 0
    elif message.text:
        pattern = r"https://t.me/(?:c/)?(.*)/(\d+)"
        matches = re.match(pattern,message.text)
        if not matches:
            return 0
        channel_id = matches.group(1)
        msg_id = int(matches.group(2))
        if channel_id.isdigit():
            if f"-100{channel_id}" == str(client.db_channel.id):
                return msg_id
        else:
            if channel_id == client.db_channel.username:
                return msg_id
    else:
        return 0


def get_readable_time(seconds: int) -> str:
    count = 0
    up_time = ""
    time_list = []
    time_suffix_list = ["s", "m", "h", "days"]
    while count < 4:
        count += 1
        remainder, result = divmod(seconds, 60) if count < 3 else divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)
    hmm = len(time_list)
    for x in range(hmm):
        time_list[x] = str(time_list[x]) + time_suffix_list[x]
    if len(time_list) == 4:
        up_time += f"{time_list.pop()}, "
    time_list.reverse()
    up_time += ":".join(time_list)
    return up_time


subscribed = filters.create(is_subscribed)
