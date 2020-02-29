from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
import discord_worker as wkr
import traceback
from datetime import datetime

loop = asyncio.get_event_loop()
old_db = AsyncIOMotorClient("mongodb://144.91.118.247:8899").xenon
new_db = AsyncIOMotorClient().xenon


async def convert_and_insert(backup):
    data = backup["template"]
    new_data = {
        "id": data["id"],
        "name": data["name"],
        "mfa_level": data.get("mfa_level", 0),
        "premium_tier": data.get("premium_tier", 0),
        "explicit_content_filter": 0,
        "large": data.get("large", False),
        "default_message_notifications": data.get("default_message_notifications", 1),
        "icon": data["icon_url"].split("/")[-1].split(".")[0] if "icon_url" in data else None,
        "system_channel_flags": data.get("system_channel_flags", 2),
        "preferred_locale": data.get("system_channel_flags", "en-US"),
        "region": data.get("region", "europe"),
        "premium_subscription_count": data.get("premium_subscription_count", 0),
        "member_count": data.get("member_count", 0),
        "features": data.get("features", []),
        "verification_level": 3,
        "owner_id": data["owner"],
        "afk_timeout": data.get("afk_timeout", 3600),
        "roles": [],
        "members": [
            {
                "nick": member.get("nick"),
                "roles": member["roles"],
                "deaf": False,
                "mute": False,
                "user": {
                    "id": member["id"],
                    "username": member["name"],
                    "discriminator": member["discriminator"]
                }
            }
            for member in data["members"]
        ],
        "bans": [
            {
                "reason": ban.get("reason"),
                "user": {
                    "id": ban["user"]
                }
            }
            for ban in data.get("bans", [])
        ],
        "channels": [],
    }

    pos_counter = 0

    for role in data["roles"]:
        new_data["roles"].append({
            **role,
            "position": role.get("position") or pos_counter
        })

        pos_counter += 1

    pos_counter = 0

    for channel in data["text_channels"]:
        new_data["channels"].append({
            "id": channel["id"],
            "name": channel["name"],
            "type": 0,
            "position": channel.get("position") or pos_counter,
            "nsfw": channel.get("nsfw", False),
            "rate_limit_per_user": channel.get("slowmode_delay", 0),
            "parent_id": channel.get("category", None),
            "topic": channel.get("topic", None),
            "permission_overwrites": [
                {
                    "id": obj_id,
                    "type": None,
                    "allow": wkr.Permissions(**{key: True for key, value in overwrites.items() if value}).value,
                    "deny": wkr.Permissions(**{key: True for key, value in overwrites.items() if not value}).value
                }
                for obj_id, overwrites in channel.get("overwrites", {}).items()
            ],
            "messages": [
                {
                    "id": msg.get("id", "0"),
                    "content": msg.get("content"),
                    "author": {
                        "id": msg["author"].get("id", "0"),
                        "username": msg["author"]["name"],
                        "discriminator": msg["author"]["discriminator"],
                        "avatar": msg["author"]["avatar_url"].split("/")[-1].split(".")[0]
                        if msg["author"].get("avatar_url") else None
                    },
                    "pinned": msg["pinned"],
                    "attachments": [
                        {
                            "filename": attachment,
                            "url": attachment
                        }
                        for attachment in msg["attachments"]
                    ],
                    "embeds": msg["embeds"]
                }
                for msg in channel.get("messages", [])
            ]
        })

        pos_counter += 1

    for channel in data["voice_channels"]:
        new_data["channels"].append({
            "id": channel["id"],
            "name": channel["name"],
            "type": 2,
            "position": channel.get("position") or pos_counter,
            "nsfw": channel.get("nsfw", False),
            "rate_limit_per_user": channel.get("slowmode_delay", 0),
            "parent_id": channel.get("category", None),
            "permission_overwrites": [
                {
                    "id": obj_id,
                    "type": None,
                    "allow": wkr.Permissions(**{key: True for key, value in overwrites.items() if value}).value,
                    "deny": wkr.Permissions(**{key: True for key, value in overwrites.items() if not value}).value
                }
                for obj_id, overwrites in channel.get("overwrites", {}).items()
            ],
            "bitrate": channel.get("bitrate", 64000),
            "user_limit": channel.get("user_limit", 0)
        })

        pos_counter += 1

    for channel in data["categories"]:
        new_data["channels"].append({
            "id": channel["id"],
            "name": channel["name"],
            "type": 4,
            "position": channel.get("position") or pos_counter,
            "nsfw": channel.get("nsfw", False),
            "permission_overwrites": [
                {
                    "id": obj_id,
                    "type": None,
                    "allow": wkr.Permissions(**{key: True for key, value in overwrites.items() if value}).value,
                    "deny": wkr.Permissions(**{key: True for key, value in overwrites.items() if not value}).value
                }
                for obj_id, overwrites in channel.get("overwrites", {}).items()
            ]
        })

        pos_counter += 1

    result = {
        "_id": str(backup["_id"]),
        "creator": str(backup["creator"]),
        "timestamp": backup.get("timestamp", datetime.utcnow()),
        "data": new_data,
        "featured": backup["featured"],
        "approved": backup["approved"],
        "uses": backup.get("uses", 0),
        "description": backup["description"]
    }

    await new_db.templates.replace_one({"_id": result["_id"]}, result, upsert=True)


async def run():
    i = 0
    async for backup in old_db.templates.find():
        i += 1
        if i % 1000 == 0:
            print(i)

        try:
            await convert_and_insert(backup)
        except:
            print(backup["_id"])
            traceback.print_exc()


loop.run_until_complete(run())
