import discord_worker as wkr


class Build(wkr.Module):
    @wkr.Module.command()
    @wkr.guild_only
    @wkr.has_permissions(administrator=True)
    @wkr.bot_has_permissions(administrator=True)
    @wkr.cooldown(1, 60, bucket=wkr.CooldownType.GUILD)
    async def build(self, ctx):
        raise ctx.f.ERROR("This command is not re-implemented yet. Please give us some time.")
