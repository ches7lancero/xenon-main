import xenon_worker as wkr
from enum import Enum
from os import environ as env


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


SUPPORT_GUILD = env.get("SUPPORT_GUILD")


class PremiumLevel(Enum):
    NONE = 0
    ONE = 1
    TWO = 2
    THREE = 3


class NotPremium(wkr.CheckFailed):
    def __init__(self, current=PremiumLevel.NONE, required=PremiumLevel.ONE):
        self.current = current
        self.required = required


def is_pro(level=PremiumLevel.ONE):
    def predicate(callback):
        async def check(ctx, *args, **kwargs):
            try:
                member = await ctx.bot.fetch_member(wkr.Snowflake(SUPPORT_GUILD), ctx.author.id)
            except wkr.NotFound:
                raise NotPremium(required=level)

            guild = await ctx.bot.get_full_guild(SUPPORT_GUILD)
            roles = member.roles_from_guild(guild)

            current = 0
            prefix = "Premium "
            for role in roles:
                if role.name.startswith(prefix):
                    try:
                        value = int(role.name.strip(prefix))
                    except ValueError:
                        continue

                    if value > current:
                        current = value

            current_level = PremiumLevel(current)
            ctx.premium = current_level

            if current < level.value:
                raise NotPremium(current=current_level, required=level)

        return wkr.Check(check, callback)

    return predicate
