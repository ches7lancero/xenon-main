import discord_worker as wkr
import utils
import asyncio
import pymongo
import pymongo.errors
from datetime import datetime

from backups import BackupSaver, BackupLoader


class TemplateListMenu(wkr.ListMenu):
    embed_kwargs = {"title": "Template List"}

    def __init__(self, ctx, search):
        super().__init__(ctx)
        self.search = search.strip()

    async def get_items(self):
        args = {
            "limit": 10,
            "skip": self.page * 10,
            "sort": [("featured", pymongo.DESCENDING), ("uses", pymongo.DESCENDING)],
            "filter": {
                "approved": True
            }
        }
        if self.search != "":
            args["filter"]["$text"] = {
                "$search": self.search
            }

        templates = self.ctx.bot.db.templates.find(**args)
        items = []
        async for template in templates:
            items.append((
                template["_id"] + ("  🌟" if template["featured"] else ""),
                template.get("description") or "No Description"
            ))

        return items


class Templates(wkr.Module):
    @wkr.Module.listener()
    async def on_load(self, *_, **__):
        await self.bot.db.templates.create_index([("_id", pymongo.TEXT), ("description", pymongo.TEXT)])

    @wkr.Module.command(aliases=("temp", "tpl"))
    async def template(self, ctx):
        """
        Create & load **PUBLIC** templates
        """
        await ctx.invoke("help backup")

    @template.command(aliases=("c",))
    @wkr.guild_only
    @wkr.has_permissions(administrator=True)
    @wkr.bot_has_permissions(administrator=True)
    @wkr.cooldown(1, 30)
    async def create(self, ctx, name, *, description):
        """
        Create a **PUBLIC** template from this server
        Use `{b.prefix}backup create` if you simply want to save or clone your server.


        __Examples__

        ```{b.prefix}template create starter A basic template for new servers```
        """
        raise ctx.f.ERROR("This command is not re-implemented yet. Please give us some time.")
        if len(description) < 30:
            raise ctx.f.ERROR("The template **description** must be at least **30 characters** long.")

        name = name.lower().replace(" ", "-").replace("_", "-")
        status_msg = await ctx.f_send("**Creating Template** ...", f=ctx.f.WORKING)

        guild = await ctx.get_full_guild()
        backup = BackupSaver(ctx.client, guild)
        await backup.save()

        try:
            await ctx.bot.db.templates.insert_one({
                "_id": name,
                "description": description,
                "creator": ctx.author.id,
                "timestamp": datetime.utcnow(),
                "uses": 0,
                "approved": False,
                "featured": False,
                "data": backup.data
            })
        except pymongo.errors.DuplicateKeyError:
            await ctx.client.edit_message(status_msg, **ctx.f.format(
                f"There is **already a template** with the **name `{name}`**.",
                f=ctx.f.ERROR
            ))
            return

        await ctx.client.edit_message(status_msg, **ctx.f.format(
            f"Successfully **created template** with the name `{name}`.\n"
            f"The template will **not appear in the template list until it was approved** by a moderator",
            f=ctx.f.SUCCESS
        ))

    @template.command(aliases=("l",))
    @wkr.guild_only
    @wkr.has_permissions(administrator=True)
    @wkr.bot_has_permissions(administrator=True)
    @wkr.cooldown(1, 60, bucket=wkr.CooldownType.GUILD)
    async def load(self, ctx, name, *options):
        """
        Load a template


        __Arguments__

        **name**: The name of the template
        **options**: A list of options (See examples)


        __Examples__

        Default options: ```{b.prefix}template load starter```
        Only roles: ```{b.prefix}template load starter !* roles```
        Everything but bans: ```{b.prefix}template load starter !bans```
        """
        template = await ctx.client.db.templates.find_one({"_id": name})
        if template is None:
            raise ctx.f.ERROR(f"There is **no template** with the name `{name}`.")

        warning_msg = await ctx.f_send("Are you sure that you want to load this template?\n"
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

        guild = await ctx.get_full_guild()
        backup = BackupLoader(ctx.client, guild, template["data"])

        options = list(options)
        options.append("!settings")
        await backup.load(**utils.backup_options(options))

    @template.command(aliases=("del", "remove", "rm"))
    @wkr.cooldown(5, 30)
    async def delete(self, ctx, name):
        result = await ctx.client.db.templates.delete_one({"_id": name, "creator": ctx.author.id})
        if result.deleted_count > 0:
            raise ctx.f.SUCCESS("Successfully **deleted template**.")

        else:
            raise ctx.f.ERROR(f"There is **no template** with the name `{name}` **created by you**.")

    @template.command(aliases=("ls", "search", "s"))
    @wkr.cooldown(1, 10)
    async def list(self, ctx, *, search):
        """
        Get a list of your backups


        __Examples__

        ```{c.prefix}backup list```
        """
        menu = TemplateListMenu(ctx, search)
        await menu.start()

    @template.command(aliases=("i",))
    @wkr.cooldown(5, 30)
    async def info(self, ctx, name):
        """
        Get information about a template


        __Arguments__

        **name**: The id of the backup or the guild id to for latest automated backup


        __Examples__

        ```{c.prefix}template info starter```
        """
        template = await ctx.client.db.templates.find_one({"_id": name})
        if template is None:
            raise ctx.f.ERROR(f"There is **no template** with the name `{name}`.")

        guild = wkr.Guild(template["data"])

        channels = utils.channel_tree(guild.channels)
        if len(channels) > 1024:
            channels = channels[:1000] + "\n...\n```"

        roles = "```{}```".format("\n".join([
            r.name for r in sorted(guild.roles, key=lambda r: r.position, reverse=True)
        ]))
        if len(roles) > 1024:
            roles = roles[:1000] + "\n...\n```"

        raise ctx.f.DEFAULT(embed={
            "title": name + (" 🌟" if template["featured"] else "") + ("  ✅" if template["approved"] else " ❌"),
            "fields": [
                {
                    "name": "Creator",
                    "value": f"<@{template['creator']}>",
                    "inline": True
                },
                {
                    "name": "Uses",
                    "value": str(template["uses"]),
                    "inline": False
                },
                {
                    "name": "Channels",
                    "value": channels,
                    "inline": True
                },
                {
                    "name": "Roles",
                    "value": roles,
                    "inline": True
                }
            ]
        })
