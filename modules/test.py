from discord_worker import Module


class TestModule(Module):
    @Module.command()
    async def yeet(self, ctx):
        await ctx.send("YEET!")

    @Module.command()
    async def channels(self, ctx):
        channel = await ctx.get_channel()
        await ctx.send(channel.name)
