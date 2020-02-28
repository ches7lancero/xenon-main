import discord_worker as wkr
import inspect
import pymongo
from datetime import timedelta, datetime

import utils
import checks


class StaffListMenu(wkr.ListMenu):
    embed_kwargs = {"title": "Staff List"}

    async def get_items(self):
        args = {
            "limit": 10,
            "skip": self.page * 10,
            "sort": [("level", pymongo.DESCENDING)],
            "filter": {}
        }
        staff_list = self.ctx.bot.db.staff.find(**args)
        items = []
        async for staff in staff_list:
            user = await self.ctx.client.fetch_user(staff["_id"])
            items.append((
                checks.StaffLevel(staff["level"]).name.lower(),
                str(user)
            ))

        return items


class Admin(wkr.Module):
    @wkr.Module.command(hidden=True)
    @wkr.is_bot_owner
    async def eval(self, ctx, *, expression):
        """
        Evaluate a singe expression and get the result
        """
        try:
            res = eval(expression)
            if inspect.isawaitable(res):
                res = await res

        except Exception as e:
            res = f"{type(e).__name__}: {str(e)}"

        raise ctx.f.SUCCESS(f"```{res}```")

    @wkr.Module.command(hidden=True)
    @checks.is_staff(level=checks.StaffLevel.ADMIN)
    async def su(self, ctx, member: wkr.MemberConverter, *, command):
        member = await member(ctx)
        ctx.msg.author = member
        await ctx.invoke(command)

    @wkr.Module.command(hidden=True)
    @checks.is_staff(level=checks.StaffLevel.MOD)
    async def gateway(self, ctx):
        bot_gw = await ctx.bot.bot_gateway()
        identifies = bot_gw["session_start_limit"]

        reset_after = timedelta(milliseconds=identifies["reset_after"])
        reset = datetime.utcnow() + reset_after

        raise ctx.f.INFO(embed={
            "fields": [
                {
                    "name": "Url",
                    "value": bot_gw["url"],
                    "inline": True
                },
                {
                    "name": "Shards",
                    "value": bot_gw["shards"],
                    "inline": True
                },
                {
                    "name": "Total Identifies",
                    "value": identifies["total"],
                    "inline": True
                },
                {
                    "name": "Remaining Identifies",
                    "value": identifies["remaining"],
                    "inline": True
                },
                {
                    "name": "Reset After",
                    "value": f"{utils.timedelta_to_string(reset_after)} ({utils.datetime_to_string(reset)})",
                    "inline": True
                }
            ]
        })

    @wkr.Module.command(hidden=True)
    @checks.is_staff()
    async def staff(self, ctx):
        """
        List all staff users
        (does not include owners)
        """
        menu = StaffListMenu(ctx)
        await menu.start()

    @staff.command()
    @wkr.is_bot_owner
    async def add(self, ctx, user: wkr.UserConverter, level="mod"):
        """
        Add a user to the staff list


        __Arguments__

        **user**: The id of the user to add to the staff list
        **level**: The staff level (e.g. admin)


        __Examples__

        Admin: ```{b.prefix}staff add 386861188891279362 admin```
        Mod: ```{b.prefix}staff add 386861188891279362 mod```
        """
        user = await user(ctx)
        try:
            level = getattr(checks.StaffLevel, level.upper())
        except AttributeError:
            raise ctx.f.ERROR(f"`{level}` is **not a valid staff level**.\n"
                              f"Choose from {', '.join([l.name.lower() for l in checks.StaffLevel])}.")

        await ctx.bot.db.staff.update_one({"_id": user.id}, {"$set": {"level": level.value}}, upsert=True)
        raise ctx.f.SUCCESS(f"Successfully **added `{user}` to the staff list**.")

    @staff.command()
    @wkr.is_bot_owner
    async def remove(self, ctx, user: wkr.UserConverter):
        """
        Remove a user from the staff list


        __Arguments__

        **user**: The id of the user to remove from the staff list


        __Examples__

        ```{b.prefix}staff add 386861188891279362```
        """
        user = await user(ctx)
        result = await ctx.bot.db.staff.delete_one({"_id": user.id})
        if result.deleted_count > 0:
            raise ctx.f.SUCCESS(f"Successfully **removed `{user}` from the staff list**.")

        else:
            raise ctx.f.ERROR(f"`{user}` is **not in the staff list**.")
