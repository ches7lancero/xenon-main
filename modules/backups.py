import discord_worker as wkr
import utils
import asyncio
import pymongo
from datetime import datetime


class BackupListMenu(wkr.ListMenu):
    embed_kwargs = {"title": "Your Backups"}

    async def get_items(self):
        args = {
            "limit": 10,
            "skip": self.page * 10,
            "sort": [("timestamp", pymongo.DESCENDING)],
            "filter": {
                "creator": self.ctx.author.id,
            }
        }
        backups = self.ctx.bot.db.backups.find(**args)
        items = []
        async for backup in backups:
            items.append((
                backup["_id"],
                f"{backup['data']['name']} (`{utils.datetime_to_string(backup['timestamp'])}`)"
            ))

        return items


class Backups(wkr.Module):
    @wkr.Module.command(aliases=("backups", "bu"))
    @wkr.has_permissions(administrator=True)
    @wkr.bot_has_permissions(administrator=True)
    async def backup(self, ctx):
        """
        Create & load private backups of your servers
        """
        await ctx.invoke("help backup")

    @backup.command(aliases=("c",))
    async def create(self, ctx):
        """
        Create a backup


        __Examples__

        ```{b.prefix}backup create```
        """
        status_msg = await ctx.f_send("**Creating Backup** ...", f=ctx.f.WORKING)

        guild = await ctx.get_guild()
        data = guild.to_dict()
        backup_id = utils.unique_id()
        await ctx.bot.db.backups.insert_one({
            "_id": backup_id,
            "creator": ctx.author.id,
            "timestamp": datetime.utcnow(),
            "data": data
        })

        embed = ctx.f.format(f"Successfully **created backup** with the id `{backup_id}`.", f=ctx.f.SUCCESS)["embed"]
        embed.setdefault("fields", []).append({
            "name": "Usage",
            "value": f"```{ctx.bot.prefix}backup load {backup_id}```\n"
                     f"```{ctx.bot.prefix}backup info {backup_id}```"
        })
        await ctx.client.edit_message(status_msg, embed=embed)

    @backup.command(aliases=("l",))
    async def load(self, ctx):
        """
        Load a backup


        __Arguments__

        **backup_id**: The id of the backup or the guild id of the latest automated backup
        **options**: A list of options (See examples)


        __Examples__

        Default options: ```{b.prefix}backup load oj1xky11871fzrbu```
        Only roles: ```{b.prefix}backup load oj1xky11871fzrbu !* roles```
        Everything but bans: ```{b.prefix}backup load oj1xky11871fzrbu !bans```
        """

    @backup.command(aliases=("del", "remove", "rm"))
    async def delete(self, ctx, backup_id):
        result = await ctx.client.db.backups.delete_one({"_id": backup_id, "creator": ctx.author.id})
        if result.deleted_count > 0:
            raise ctx.f.SUCCESS("Successfully **deleted backup**.")

        else:
            raise ctx.f.ERROR(f"You have **no backup** with the id `{backup_id}`.")

    @backup.command(aliases=("clear",))
    async def purge(self, ctx):
        """
        Delete all your backups
        __**This cannot be undone**__


        __Examples__

        ```{b.prefix}backup purge```
        """
        warning_msg = await ctx.f_send("Are you sure that you want to delete all your backups?\n"
                                       "__**This cannot be undone!**__", f=ctx.f.WARNING)
        reactions = ("✅", "❌")
        for reaction in reactions:
            await ctx.client.add_reaction(warning_msg, reaction)

        try:
            data, = await ctx.client.wait_for(
                "message_reaction_add",
                ctx.shard_id,
                check=lambda d: d["message_id"] == warning_msg.id and
                                d["user_id"] == ctx.author.id and
                                d["emoji"]["name"] in reactions,
                timeout=60
            )
        except asyncio.TimeoutError:
            await ctx.client.delete_message(warning_msg)
            return

        await ctx.client.delete_message(warning_msg)
        if data["emoji"]["name"] != "✅":
            return

        await ctx.client.db.backups.delete_many({"creator": ctx.author.id})
        raise ctx.f.SUCCESS("Deleted all your backups.")

    @backup.command(aliases=("ls",))
    async def list(self, ctx):
        """
        Get a list of your backups


        __Examples__

        ```{c.prefix}backup list```
        """
        menu = BackupListMenu(ctx)
        await menu.start()

    @backup.command(aliases=("i",))
    async def info(self, ctx):
        """
        Get information about a backup


        __Arguments__

        **backup_id**: The id of the backup or the guild id to for latest automated backup


        __Examples__

        ```{c.prefix}backup info oj1xky11871fzrbu```
        """

    @backup.command(aliases=("iv",))
    async def interval(self, ctx):
        """
        Setup automated backups


        __Arguments__

        **interval**: The time between every backup or "off".
                    Supported units: minutes(m), hours(h), days(d), weeks(w), month(m)
                    Example: 1d 12h


        __Examples__

        ```{c.prefix}backup interval 24h```
        """
