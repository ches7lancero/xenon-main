import xenon_worker as wkr
import pymongo
import pymongo.errors
from enum import Enum, IntEnum

import checks
import utils


class SyncDirection(Enum):
    FROM = 0
    TO = 1
    BOTH = 2


class SyncType(IntEnum):
    MESSAGES = 0
    BANS = 1


class Sync(wkr.Module):
    @wkr.Module.listener()
    async def on_load(self, *_, **__):
        await self.bot.db.syncs.create_index(
            [("type", pymongo.ASCENDING), ("target", pymongo.ASCENDING), ("source", pymongo.ASCENDING)],
            unique=True
        )

        await self.bot.subscribe("*.message_create", shared=True)
        await self.bot.subscribe("*.guild_ban_add", shared=True)
        await self.bot.subscribe("*.guild_ban_remove", shared=True)

    @wkr.Module.command()
    @wkr.guild_only
    @wkr.has_permissions(administrator=True)
    @wkr.bot_has_permissions(administrator=True)
    @checks.is_premium()
    async def sync(self, ctx):
        """
        Sync messages and bans between different servers and channels
        """
        await ctx.invoke("help sync")

    @sync.command(aliases=("ls",))
    async def list(self, ctx):
        pass

    async def _check_admin_on(self, guild, ctx):
        try:
            invoker = await self.client.fetch_member(guild, ctx.author.id)
        except wkr.NotFound:
            raise ctx.f.ERROR("You **need to be member** of the target guild.")

        perms = invoker.permissions_for_guild(guild)
        if not perms.administrator:
            raise ctx.f.ERROR("You **need to have `administrator`** in the target guild.")

        bot = await self.client.get_bot_member(guild.id)
        if bot is None:
            raise ctx.f.ERROR("The bot **needs to be member** of the target guild.")

        bot_perms = bot.permissions_for_guild(guild)
        if not bot_perms.administrator:
            raise ctx.f.ERROR("The bot **needs to have `administrator`** in the target guild.")

    @sync.command(aliases=("channels", "msg"))
    async def messages(self, ctx, direction, target: wkr.ChannelConverter):
        try:
            direction = getattr(SyncDirection, direction.upper())
        except AttributeError:
            raise ctx.f.ERROR(f"`{direction}` is **not a valid sync direction**.\n"
                              f"Choose from `{', '.join([l.name.lower() for l in SyncDirection])}`.")

        channel = await target(ctx)
        guild = await self.client.get_full_guild(channel.guild_id)
        await self._check_admin_on(guild, ctx)

        async def _create_msg_sync(target_id, source_id):
            webh = await ctx.client.create_webhook(wkr.Snowflake(target_id), name="sync")
            sync_id = utils.unique_id()
            try:
                await ctx.bot.db.syncs.insert_one({
                    "_id": sync_id,
                    "type": SyncType.MESSAGES,
                    "target": target_id,
                    "source": source_id,
                    "webhook": webh.to_dict()
                })
            except pymongo.errors.DuplicateKeyError:
                await ctx.f_send(
                    f"Sync from <#{source_id}> to <#{target_id}> **already exists**.",
                    f=ctx.f.INFO
                )

            else:
                await ctx.f_send(
                    f"Successfully **created sync** from <#{source_id}> to <#{target_id}>",
                    f=ctx.f.SUCCESS
                )

        if direction == SyncDirection.FROM or direction == SyncDirection.BOTH:
            await _create_msg_sync(ctx.channel_id, channel.id)

        if direction == SyncDirection.TO or direction == SyncDirection.BOTH:
            await _create_msg_sync(channel.id, ctx.channel_id)

    @wkr.Module.listener()
    async def on_message_create(self, _, data):
        msg = wkr.Message(data)
        if msg.webhook_id:
            return

        syncs = self.bot.db.syncs.find({"source": msg.channel_id, "type": SyncType.MESSAGES})
        async for sync in syncs:
            webh = wkr.Webhook(sync["webhook"])
            await self.client.execute_webhook(
                webh,
                username=msg.author.name,
                avatar_url=msg.author.avatar_url,
                **msg.to_dict()
            )

    @sync.command()
    async def bans(self, ctx, direction, target: wkr.GuildConverter):
        try:
            direction = getattr(SyncDirection, direction.upper())
        except AttributeError:
            raise ctx.f.ERROR(f"`{direction}` is **not a valid sync direction**.\n"
                              f"Choose from `{', '.join([l.name.lower() for l in SyncDirection])}`.")

        guild = await target(ctx)
        await self._check_admin_on(guild, ctx)
