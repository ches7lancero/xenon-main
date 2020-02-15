from discord_worker import Module


class TestModule(Module):
    @Module.command()
    async def yeet(self, ctx):
        await ctx.send("YEET!")

    @Module.command()
    async def author(self, ctx):
        await ctx.send(ctx.author.name)

    @Module.command()
    async def channel(self, ctx):
        channel = await ctx.get_channel()
        if channel is None:
            await ctx.send(":(")

        else:
            await ctx.send(channel.name)

    @Module.command()
    async def guild(self, ctx):
        guild = await ctx.get_guild()
        if guild is None:
            await ctx.send(":(")

        else:
            await ctx.send(guild.name)

    @Module.command()
    async def bot(self, ctx):
        bot = await ctx.bot.get_bot_member(ctx.guild_id)
        if bot is None:
            await ctx.send(":(")

        else:
            await ctx.send(bot.name)
