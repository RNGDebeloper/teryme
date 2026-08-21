from datetime import datetime
from typing import Any, Dict, Optional

from database.database import database

ad_settings = database["ad_settings"] if database is not None else None
verification_tokens = database["verification_tokens"] if database is not None else None
ads_completions = database["ads_completions"] if database is not None else None
ads_stats = database["ads_stats"] if database is not None else None


DEFAULT_AD_SETTINGS: Dict[str, Any] = {
    "_id": "global",
    "ads_enabled": False,
    "rewarded_popup_enabled": False,
    "interstitial_enabled": False,
    "rewarded_popup_zone": "",
    "interstitial_script": "",
    "mode": "rewarded_popup",  # rewarded_popup | interstitial | both
    "updated_at": datetime.utcnow(),
}

DEFAULT_AD_STATS: Dict[str, Any] = {
    "_id": "global",
    "completed_ads": 0,
    "files_unlocked": 0,
    "tier_1_users": 0,
    "tier_2_users": 0,
    "tier_3_users": 0,
    "updated_at": datetime.utcnow(),
}

TIER_1 = {"US", "GB", "UK", "CA", "AU", "DE"}
TIER_2 = {"AE", "UAE", "SG", "FR", "IT", "ES"}


async def get_ad_settings() -> Dict[str, Any]:
    if ad_settings is None:
        return DEFAULT_AD_SETTINGS.copy()

    settings = ad_settings.find_one({"_id": "global"})
    if settings:
        merged = DEFAULT_AD_SETTINGS.copy()
        merged.update(settings)
        return merged

    ad_settings.insert_one(DEFAULT_AD_SETTINGS.copy())
    return DEFAULT_AD_SETTINGS.copy()


async def update_ad_settings(patch: Dict[str, Any]) -> Dict[str, Any]:
    if ad_settings is None:
        mock = DEFAULT_AD_SETTINGS.copy()
        mock.update(patch)
        return mock

    patch = {**patch, "updated_at": datetime.utcnow()}
    ad_settings.update_one({"_id": "global"}, {"$set": patch}, upsert=True)
    return await get_ad_settings()


async def create_verification_token(payload: Dict[str, Any]) -> Optional[str]:
    if verification_tokens is None:
        return None
    verification_tokens.insert_one(payload)
    return payload["token"]


async def get_verification_token(token: str) -> Optional[Dict[str, Any]]:
    if verification_tokens is None:
        return None
    return verification_tokens.find_one({"token": token})


async def update_verification_token(token: str, patch: Dict[str, Any]) -> None:
    if verification_tokens is None:
        return
    verification_tokens.update_one({"token": token}, {"$set": patch})


def country_to_tier(country_code: str) -> str:
    code = (country_code or "").strip().upper()
    if code in TIER_1:
        return "Tier1"
    if code in TIER_2:
        return "Tier2"
    return "Tier3"


async def get_ads_stats() -> Dict[str, Any]:
    if ads_stats is None:
        return DEFAULT_AD_STATS.copy()

    doc = ads_stats.find_one({"_id": "global"})
    if doc:
        merged = DEFAULT_AD_STATS.copy()
        merged.update(doc)
        return merged

    ads_stats.insert_one(DEFAULT_AD_STATS.copy())
    return DEFAULT_AD_STATS.copy()


async def increment_files_unlocked() -> None:
    if ads_stats is None:
        return
    ads_stats.update_one(
        {"_id": "global"},
        {"$inc": {"files_unlocked": 1}, "$set": {"updated_at": datetime.utcnow()}},
        upsert=True,
    )


async def record_ad_completion(
    *,
    token: str,
    user_id: int,
    bot_id: Optional[int],
    file_id: str,
    country: str,
) -> bool:
    """Persist one ad completion and increment aggregate counters once per token."""
    if ads_completions is None or ads_stats is None:
        return False

    tier = country_to_tier(country)
    completion_doc = {
        "token": token,
        "user_id": user_id,
        "bot_id": bot_id,
        "file_id": file_id,
        "completed": True,
        "timestamp": datetime.utcnow(),
        "country": (country or "Unknown").upper(),
        "tier": tier,
    }

    result = ads_completions.update_one(
        {"token": token},
        {"$setOnInsert": completion_doc},
        upsert=True,
    )
    if not result.upserted_id:
        return False

    tier_field = {
        "Tier1": "tier_1_users",
        "Tier2": "tier_2_users",
        "Tier3": "tier_3_users",
    }[tier]

    ads_stats.update_one(
        {"_id": "global"},
        {
            "$inc": {"completed_ads": 1, tier_field: 1},
            "$set": {"updated_at": datetime.utcnow()},
        },
        upsert=True,
    )
    return True
