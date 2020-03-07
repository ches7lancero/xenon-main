import discord_worker as wkr
from enum import Enum


class StaffLevel(Enum):
    NONE = -1
    MOD = 0
    ADMIN = 1


class NotStaff(wkr.CheckFailed):
    def __init__(self, current=StaffLevel.NONE, required=StaffLevel.MOD):
        self.current = current
        self.required = required


def is_staff(level=StaffLevel.MOD):
    def predicate(callback):
        async def check(ctx, *args, **kwargs):
            staff = await ctx.bot.db.staff.find_one({"_id": ctx.author.id})
            if staff is None:
                raise NotStaff(required=level)

            if staff["level"] < level.value:
                raise NotStaff(current=StaffLevel(staff["level"]), required=level)

            return True

        return wkr.Check(check, callback)

    return predicate
