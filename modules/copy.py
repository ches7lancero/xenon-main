import xenon_worker as wkr


class Copy(wkr.Module):
    @wkr.Module.command(hidden=True)
    async def copy(self, ctx):
        raise ctx.f.INFO("The copy command is **currently not available**.\n"
                         "Please create and then load a backup instead.")
