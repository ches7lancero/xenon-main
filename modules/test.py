from discord_worker import Module


class TestModule(Module):
    @Module.command()
    async def yeet(self, ctx):
        await ctx.send("YEET!")

    @Module.command()
    async def channel(self, ctx):
        channel = await ctx.get_channel()
        await ctx.send(channel.name)

    @Module.command()
    async def guild(self, ctx):
        guild = await ctx.get_guild()
        await ctx.send(guild.name)
