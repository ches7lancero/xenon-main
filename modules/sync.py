import xenon_worker as wkr

import checks


class Sync(wkr.Module):
    @wkr.Module.command()
    @wkr.guild_only
    @wkr.has_permissions(administrator=True)
    @wkr.bot_has_permissions(administrator=True)
    @checks.is_premium()
    async def sync(self, ctx):
        pass

    @sync.command(aliases=("ls",))
    async def list(self, ctx):
        pass

    @sync.command(aliases=("channels", "msg"))
    async def messages(self, ctx):
        pass

    @sync.command()
    async def bans(self, ctx):
        pass
