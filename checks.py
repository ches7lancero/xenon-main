import discord_worker as wkr
from enum import Enum


class StaffLevel(Enum):
    MOD = 0
    ADMIN = 1


class NotStaff(wkr.CheckFailed):
    def __init__(self, level=StaffLevel.MOD):
        self.level = level


def is_staff(level=StaffLevel.MOD):
    def predicate(callback):
        async def check(ctx, *args, **kwargs):
            staff = await ctx.bot.db.staff.find_one({"_id": ctx.author.id})
            if staff is None:
                raise NotStaff(level)

            if staff["level"] < level.value:
                raise NotStaff(level)

            return True

        return wkr.Check(callback, check)

    return predicate
