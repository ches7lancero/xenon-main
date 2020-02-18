import discord_worker as wkr
import inspect
import pymongo

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
    @wkr.Module.command()
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

    @wkr.Module.command()
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
