from datetime import datetime
from typing import List

from pymongo.errors import PyMongoError

from database.database import database

premium_users = database["premium_users"] if database is not None else None


async def add_premium_user(user_id: int, added_by: int) -> bool:
    if premium_users is None:
        return False
    try:
        premium_users.update_one(
            {"_id": user_id},
            {"$set": {"added_by": added_by, "updated_at": datetime.utcnow()}},
            upsert=True,
        )
        return True
    except PyMongoError:
        return False


async def remove_premium_user(user_id: int) -> bool:
    if premium_users is None:
        return False
    try:
        premium_users.delete_one({"_id": user_id})
        return True
    except PyMongoError:
        return False


async def is_premium_user(user_id: int) -> bool:
    if premium_users is None:
        return False
    try:
        return bool(premium_users.find_one({"_id": user_id}))
    except PyMongoError:
        return False


async def list_premium_users() -> List[int]:
    if premium_users is None:
        return []
    try:
        return [doc["_id"] for doc in premium_users.find({}, {"_id": 1})]
    except PyMongoError:
        return []
