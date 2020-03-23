import xenon_worker as wkr
import pymongo

import checks


class Sync(wkr.Module):
    @wkr.Module.listener()
    async def on_load(self, *_, **__):
        await self.bot.db.syncs.create_index([("target", pymongo.ASCENDING)])
        await self.bot.db.syncs.create_index([("source", pymongo.ASCENDING)])

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

    @sync.command(aliases=("channels", "msg"))
    async def messages(self, ctx):
        pass

    @sync.command()
    async def bans(self, ctx):
        pass
