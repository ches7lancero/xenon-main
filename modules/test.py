from discord_worker import Module


class TestModule(Module):
    @Module.command()
    async def yeet(self, ctx):
        await ctx.send("YEET!")
