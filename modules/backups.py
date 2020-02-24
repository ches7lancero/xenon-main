import discord_worker as wkr
import utils
import asyncio
import pymongo
from datetime import datetime, timedelta
import random

from backups import BackupSaver, BackupLoader


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
                f"{backup['data']['name']} (`{utils.datetime_to_string(backup['timestamp'])} UTC`)"
            ))

        return items


class Backups(wkr.Module):
    @wkr.Module.command(aliases=("backups", "bu"))
    async def backup(self, ctx):
        """
        Create & load private backups of your servers
        """
        await ctx.invoke("help backup")

    @backup.command(aliases=("c",))
    @wkr.guild_only
    @wkr.has_permissions(administrator=True)
    @wkr.bot_has_permissions(administrator=True)
    @wkr.cooldown(1, 10, bucket=wkr.CooldownType.GUILD)
    async def create(self, ctx):
        """
        Create a backup


        __Examples__

        ```{b.prefix}backup create```
        """
        status_msg = await ctx.f_send("**Creating Backup** ...", f=ctx.f.WORKING)

        guild = await ctx.get_guild()
        backup = BackupSaver(ctx.client, guild)
        await backup.save()

        backup_id = utils.unique_id()
        await ctx.bot.db.backups.insert_one({
            "_id": backup_id,
            "creator": ctx.author.id,
            "timestamp": datetime.utcnow(),
            "data": backup.data
        })

        embed = ctx.f.format(f"Successfully **created backup** with the id `{backup_id}`.", f=ctx.f.SUCCESS)["embed"]
        embed.setdefault("fields", []).append({
            "name": "Usage",
            "value": f"```{ctx.bot.prefix}backup load {backup_id}```\n"
                     f"```{ctx.bot.prefix}backup info {backup_id}```"
        })
        await ctx.client.edit_message(status_msg, embed=embed)

    @backup.command(aliases=("l",))
    @wkr.guild_only
    @wkr.has_permissions(administrator=True)
    @wkr.bot_has_permissions(administrator=True)
    @wkr.cooldown(1, 60, bucket=wkr.CooldownType.GUILD)
    async def load(self, ctx, backup_id, *options):
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
        backup_d = await ctx.client.db.backups.find_one({"_id": backup_id, "creator": ctx.author.id})
        if backup_d is None:
            raise ctx.f.ERROR(f"You have **no backup** with the id `{backup_id}`.")

        warning_msg = await ctx.f_send("Are you sure that you want to load this backup?\n"
                                       "__**All channels and roles will get replaced!**__", f=ctx.f.WARNING)
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

        guild = await ctx.get_guild()
        backup = BackupLoader(ctx.client, guild, backup_d["data"])
        await backup.load(**utils.backup_options(options))

    @backup.command(aliases=("del", "remove", "rm"))
    @wkr.cooldown(5, 30)
    async def delete(self, ctx, backup_id):
        result = await ctx.client.db.backups.delete_one({"_id": backup_id, "creator": ctx.author.id})
        if result.deleted_count > 0:
            raise ctx.f.SUCCESS("Successfully **deleted backup**.")

        else:
            raise ctx.f.ERROR(f"You have **no backup** with the id `{backup_id}`.")

    @backup.command(aliases=("clear",))
    @wkr.cooldown(1, 60, bucket=wkr.CooldownType.GUILD)
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
    @wkr.cooldown(1, 10)
    async def list(self, ctx):
        """
        Get a list of your backups


        __Examples__

        ```{c.prefix}backup list```
        """
        menu = BackupListMenu(ctx)
        await menu.start()

    @backup.command(aliases=("i",))
    @wkr.cooldown(5, 30)
    async def info(self, ctx, backup_id):
        """
        Get information about a backup


        __Arguments__

        **backup_id**: The id of the backup or the guild id to for latest automated backup


        __Examples__

        ```{c.prefix}backup info oj1xky11871fzrbu```
        """
        backup = await ctx.client.db.backups.find_one({"_id": backup_id, "creator": ctx.author.id})
        if backup is None:
            raise ctx.f.ERROR(f"You have **no backup** with the id `{backup_id}`.")

        guild = wkr.Guild(backup["data"])

        channel_text = utils.channel_tree(guild.channels)
        if len(channel_text) > 1024:
            channel_text = channel_text[:1019] + "\n..."

        voice_text = "```{}```".format("\n".join([
            r.name for r in sorted(guild.roles, key=lambda r: r.position, reverse=True)
        ]))
        if len(voice_text) > 1024:
            voice_text = voice_text[:1019] + "\n..."

        raise ctx.f.DEFAULT(embed={
            "title": guild.name,
            "fields": [
                {
                    "name": "Created At",
                    "value": utils.datetime_to_string(backup["timestamp"]) + " UTC",
                    "inline": False
                },
                {
                    "name": "Channels",
                    "value": channel_text,
                    "inline": True
                },
                {
                    "name": "Roles",
                    "value": voice_text,
                    "inline": True
                }
            ]
        })

    @backup.command(aliases=("iv",))
    @wkr.guild_only
    @wkr.has_permissions(administrator=True)
    @wkr.bot_has_permissions(administrator=True)
    @wkr.cooldown(1, 10, bucket=wkr.CooldownType.GUILD)
    async def interval(self, ctx, *interval):
        """
        Manage automated backups


        __Arguments__

        **interval**: The time between every backup or "off". (min 24h)
                    Supported units: hours(h), days(d), weeks(w)
                    Example: 1d 12h


        __Examples__

        ```{c.prefix}backup interval 24h```
        """
        if len(interval) > 0:
            await ctx.invoke("backup interval on " + " ".join(interval))
            return

        interval = await ctx.bot.db.intervals.find_one({"_id": ctx.guild_id})
        if interval is None:
            raise ctx.f.INFO("The **backup interval is** currently turned **off**.\n"
                             f"Turn it on with `{ctx.bot.prefix}backup interval on 24h`.")

    @interval.command(aliases=["enable"])
    @wkr.guild_only
    @wkr.has_permissions(administrator=True)
    @wkr.bot_has_permissions(administrator=True)
    @wkr.cooldown(1, 10, bucket=wkr.CooldownType.GUILD)
    async def on(self, ctx, *interval):
        """
        Turn on automated backups


        __Arguments__

        **interval**: The time between every backup. (min 24h)
                    Supported units: hours(h), days(d), weeks(w)
                    Example: 1d 12h


        __Examples__

        ```{c.prefix}backup interval on 24h```
        """
        units = {
            "h": 1,
            "d": 24,
            "w": 24 * 7
        }

        hours = 0
        for arg in interval:
            count, unit = int(arg[:-1]), arg[-1]
            multiplier = units.get(unit.lower(), 1)
            hours += count * multiplier

        # hours = min(hours, 24)

        now = datetime.utcnow()
        td = timedelta(hours=hours)
        await ctx.bot.db.intervals.update_one({"_id": ctx.guild_id}, {"$set": {
            "_id": ctx.guild_id,
            "last": now,
            "next": now + td,
            "interval": hours
        }}, upsert=True)

        raise ctx.f.SUCCESS("Successful **enabled the backup interval**.\nThe first backup will be created in "
                            f"`{utils.timedelta_to_string(td)}` "
                            f"at `{utils.datetime_to_string(datetime.utcnow() + td)} UTC`.")

    @interval.command(aliases=["disable"])
    @wkr.guild_only
    @wkr.has_permissions(administrator=True)
    @wkr.bot_has_permissions(administrator=True)
    @wkr.cooldown(1, 10, bucket=wkr.CooldownType.GUILD)
    async def off(self, ctx):
        """
        Turn off automated backups


        __Examples__

        ```{c.prefix}backup interval off```
        """
        result = await ctx.bot.db.intervals.delete_one({"_id": ctx.guild_id})
        if result.deleted_count > 0:
            raise ctx.f.SUCCESS("Successfully **disabled the backup interval**.")

        else:
            raise ctx.f.ERROR(f"The backup interval is not enabled.")

    async def run_interval_backups(self, guild_id):
        guild = await self.bot.get_guild(guild_id)
        backup = BackupSaver(self.bot, guild)
        await backup.save()

        await self.bot.db.backups.replace_one({"_id": guild_id}, {
            "_id": guild_id,
            "creator": guild.owner_id,
            "timestamp": datetime.utcnow(),
            "interval": True,
            "data": backup.data
        }, upsert=True)

    @wkr.Module.task(minutes=random.randint(5, 15))
    async def interval_task(self):
        to_backup = self.bot.db.intervals.find({"next": {"$lt": datetime.utcnow()}})
        async for interval in to_backup:
            guild_id = interval["_id"]
            self.bot.schedule(self.run_interval_backups(guild_id))
            await self.bot.db.intervals.update_one({"_id": guild_id}, {"$set": {
                "next": interval["next"] + timedelta(hours=interval["interval"])
            }})
