import xenon_worker as wkr
import utils
import asyncio
import pymongo
import pymongo.errors
from datetime import datetime
from os import environ as env

from backups import BackupSaver, BackupLoader
import checks


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
    APPROVAL_CHANNEL = env.get("TPL_APPROVAL_CHANNEL")
    LIST_CHANNEL = env.get("TPL_LIST_CHANNEL")
    FEATURED_CHANNEL = env.get("TPL_FEATURED_CHANNEL")
    APPROVAL_GUILD = env.get("TPL_APPROVAL_GUILD")
    APPROVAL_OPTIONS = {}

    @wkr.Module.listener()
    async def on_load(self, *_, **__):
        await self.bot.db.templates.create_index([("_id", pymongo.TEXT), ("description", pymongo.TEXT)])
        await self.bot.db.backups.create_index([("approved", pymongo.ASCENDING)])
        await self.bot.db.backups.create_index([("featured", pymongo.ASCENDING)])
        await self.bot.db.backups.create_index([("uses", pymongo.ASCENDING)])
        # Subscribe to message_reaction_add on the approval guild
        shard_id = await self.client.guild_shard(self.APPROVAL_GUILD)
        await self.bot.subscribe(f"{shard_id}.message_reaction_add", shared=True)
        self.APPROVAL_OPTIONS = {
            "✅": self._approve,
            "⭐": self._feature,
            "⛔": self._delete,
            "❔": self._delete_because("Insufficient name and/or description, please fill them in and resubmit again."),
            "🙅": self._delete_because("Not a template, just a copy of your server, use a backup instead. "
                                       "Templates are for everyone, not specifically for you, they must be generic.")
        }

    @wkr.Module.command(aliases=("temp", "tpl"))
    async def template(self, ctx):
        """
        Create & load **PUBLIC** templates
        """
        await ctx.invoke("help template")

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
        if len(description) < 30:
            raise ctx.f.ERROR("The template **description** must be at least **30 characters** long.")

        name = name.lower().replace(" ", "-").replace("_", "-")
        status_msg = await ctx.f_send("**Creating Template** ...", f=ctx.f.WORKING)

        guild = await ctx.get_full_guild()
        backup = BackupSaver(ctx.client, guild)
        await backup.save()

        template = {
            "_id": name,
            "description": description,
            "creator": ctx.author.id,
            "timestamp": datetime.utcnow(),
            "uses": 0,
            "approved": False,
            "featured": False,
            "data": backup.data
        }

        try:
            await ctx.bot.db.templates.insert_one(template)
        except pymongo.errors.DuplicateKeyError:
            await ctx.client.edit_message(status_msg, **ctx.f.format(
                f"There is **already a template** with the **name `{name}`**.",
                f=ctx.f.ERROR
            ))
            return

        await ctx.client.edit_message(status_msg, **ctx.f.format(
            f"Successfully **created template** with the name `{name}`.\n"
            f"The template will **not appear in the template list until it was approved** by a moderator.",
            f=ctx.f.SUCCESS
        ))

        await self._send_to_approval(template)

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
        backup = BackupLoader(ctx.client, guild, template["data"], reason="Template loaded by " + str(ctx.author))

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

        All templates: ```{b.prefix}template list```
        Search: ```{b.prefix}template search roleplay```
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

        ```{b.prefix}template info starter```
        """
        template = await ctx.client.db.templates.find_one({"_id": name})
        if template is None:
            raise ctx.f.ERROR(f"There is **no template** with the name `{name}`.")

        raise ctx.f.DEFAULT(embed=self._template_info(template))

    def _template_info(self, template):
        guild = wkr.Guild(template["data"])

        channels = utils.channel_tree(guild.channels)
        if len(channels) > 1024:
            channels = channels[:1000] + "\n...\n```"

        roles = "```{}```".format("\n".join([
            r.name for r in sorted(guild.roles, key=lambda r: r.position, reverse=True)
        ]))
        if len(roles) > 1024:
            roles = roles[:1000] + "\n...\n```"

        return {
            "title": template["_id"] + (
                " 🌟" if template["featured"] else ""
            ) + (
                         "  ✅" if template["approved"] else " ❌"
                     ),
            "description": template["description"],
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
        }

    @template.command(hidden=True)
    @checks.is_staff(level=checks.StaffLevel.MOD)
    async def approve(self, ctx, tpl_name):
        template = await self.client.db.templates.find_one({"_id": tpl_name})
        if template is None:
            raise ctx.f.ERROR(f"There is **no template** with the name `{tpl_name}`.")

        await self.approve(template)
        raise ctx.f.SUCCESS("Successfully **approved template**.")

    @template.command(hidden=True)
    @checks.is_staff(level=checks.StaffLevel.MOD)
    async def feature(self, ctx, tpl_name):
        template = await self.client.db.templates.find_one({"_id": tpl_name})
        if template is None:
            raise ctx.f.ERROR(f"There is **no template** with the name `{tpl_name}`.")

        await self._feature(template)
        raise ctx.f.SUCCESS("Successfully **featured template**.")

    @template.command(hidden=True)
    @checks.is_staff(level=checks.StaffLevel.MOD)
    async def deny(self, ctx, tpl_name, *, reason):
        template = await self.client.db.templates.find_one({"_id": tpl_name})
        if template is None:
            raise ctx.f.ERROR(f"There is **no template** with the name `{tpl_name}`.")

        await self._delete_because(reason)(template)
        raise ctx.f.SUCCESS("Successfully **denied / deleted template**.")

    async def _send_to_approval(self, template):
        msg = await self.client.f_send(
            wkr.Snowflake(self.APPROVAL_CHANNEL),
            embed=self._template_info(template)
        )
        for option in self.APPROVAL_OPTIONS.keys():
            await self.client.add_reaction(msg, option)

    @wkr.Module.listener()
    async def on_message_reaction_add(self, shard_id, data):
        if data["channel_id"] != self.APPROVAL_CHANNEL or data["user_id"] == self.bot.user.id:
            return

        action = self.APPROVAL_OPTIONS.get(data["emoji"]["name"])
        if action is None:
            return

        try:
            msg = await self.client.fetch_message(wkr.Snowflake(data["channel_id"]), data["message_id"])
        except wkr.NotFound:
            return

        if len(msg.embeds) == 0:
            return

        tpl_name = msg.embeds[0].get("title", "").strip(" ✅❌")
        if tpl_name == "":
            return

        template = await self.client.db.templates.find_one({"_id": tpl_name})
        if template is not None:
            await action(template, data["channel_id"])

        await self.client.delete_message(msg)

    def _delete_because(self, reason):
        async def predicate(template, *args):
            await self.client.db.templates.delete_one({"_id": template["_id"]})
            dm_channel = await self.client.start_dm(wkr.Snowflake(template["creator"]))
            await self.client.f_send(
                dm_channel,
                f"Your **template `{template['_id']}` got denied**.```\n{reason}\n```",
                f=self.client.f.INFO
            )

        return predicate

    async def _delete(self, template, channel_id):
        shard_id = await self.client.guild_shard(self.APPROVAL_GUILD)
        data, = await self.client.wait_for(
            event="message_create",
            shard_id=shard_id,
            check=lambda d: d["channel_id"] == channel_id,
            timeout=60
        )
        msg = wkr.Message(data)
        await self.client.delete_message(msg)
        await self._delete_because(msg.content)(template)

    async def _feature(self, template, *args):
        await self.client.db.templates.update_one({"_id": template["_id"]}, {"$set": {
            "approved": True,
            "featured": True
        }})
        template["approved"] = True
        template["featured"] = True
        dm_channel = await self.client.start_dm(wkr.Snowflake(template["creator"]))
        await self.client.f_send(
            dm_channel,
            f"Your **template `{template['_id']}` got featured**.",
            f=self.client.f.INFO
        )
        await self.client.f_send(wkr.Snowflake(self.LIST_CHANNEL), embed=self._template_info(template))

    async def _approve(self, template, *args):
        await self.client.db.templates.update_one({"_id": template["_id"]}, {"$set": {
            "approved": True
        }})
        template["approved"] = True
        dm_channel = await self.client.start_dm(wkr.Snowflake(template["creator"]))
        await self.client.f_send(
            dm_channel,
            f"Your **template `{template['_id']}` got approved**.",
            f=self.client.f.INFO
        )
        await self.client.f_send(wkr.Snowflake(self.LIST_CHANNEL), embed=self._template_info(template))
