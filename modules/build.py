import xenon_worker as wkr


class Build(wkr.Module):
    @wkr.Module.command(hidden=True)
    @wkr.guild_only
    @wkr.has_permissions(administrator=True)
    @wkr.bot_has_permissions(administrator=True)
    @wkr.cooldown(1, 60, bucket=wkr.CooldownType.GUILD)
    async def build(self, ctx):
        raise ctx.f.ERROR("This command is **currently not available**. It might come back in the future.\n"
                          "Please don't ask us when it will come back, there is **no ETA**.")
