from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pymongo.errors import PyMongoError

from config import FORCE_MSG, FORCE_SUB_CHANNEL, START_PIC
from database.database import database

bot_settings = database["bot_settings"] if database is not None else None


DEFAULT_SETTINGS: Dict[str, Any] = {
    "force_sub_channel": FORCE_SUB_CHANNEL,
    "start_pic": START_PIC,
    "force_msg": FORCE_MSG,
    "force_pic": "",
    "updated_at": datetime.utcnow(),
}


def _doc_id(bot_id: int) -> str:
    return f"bot:{bot_id}"


async def get_bot_settings(bot_id: int) -> Dict[str, Any]:
    settings = DEFAULT_SETTINGS.copy()
    if bot_settings is None:
        return settings

    try:
        saved = bot_settings.find_one({"_id": _doc_id(bot_id)})
    except PyMongoError:
        return settings

    if saved:
        settings.update(saved)
    return settings


async def update_bot_settings(bot_id: int, patch: Dict[str, Any]) -> Dict[str, Any]:
    if bot_settings is None:
        local = DEFAULT_SETTINGS.copy()
        local.update(patch)
        return local

    payload = {**patch, "updated_at": datetime.utcnow()}
    try:
        bot_settings.update_one({"_id": _doc_id(bot_id)}, {"$set": payload}, upsert=True)
    except PyMongoError:
        pass

    return await get_bot_settings(bot_id)


async def get_force_sub_channel(bot_id: int) -> Optional[int]:
    settings = await get_bot_settings(bot_id)
    channel = settings.get("force_sub_channel")
    if isinstance(channel, int) and channel != 0:
        return channel
    return None
