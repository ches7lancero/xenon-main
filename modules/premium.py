import xenon_worker as wkr


class Premium(wkr.Module):
    @wkr.Module.command(aliases=("chatlog", "chatlogs"))
    async def chatlog(self, ctx):
        """
        Save & load messages from individual channels
        """
        await ctx.f_send("This command can **only** be used with **Xenon Premium**.", f=ctx.f.INFO)
        await ctx.invoke("premium")

    @wkr.Module.command()
    async def sync(self, ctx):
        """
        Sync messages and bans between different servers and channels
        """
        await ctx.f_send("This command can **only** be used with **Xenon Premium**.", f=ctx.f.INFO)
        await ctx.invoke("premium")
