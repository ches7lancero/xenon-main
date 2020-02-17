import discord_worker as wkr
import random
from datetime import datetime


def make_id():
    """
    Generates a unique id consisting of the the unix timestamp in milliseconds and 16 random bits
    """
    unix_t = int(datetime.utcnow().timestamp() * 1000)
    result = (unix_t << (64 - unix_t.bit_length())) | (random.getrandbits(16))
    return hex(result)[2:]


class Backups(wkr.Module):
    @wkr.Module.command()
    @wkr.has_permissions(administrator=True)
    @wkr.bot_has_permissions(administrator=True)
    async def backup(self, ctx):
        """
        Create & load private backups of your servers
        """
        await ctx.invoke("help backup")

    @backup.command()
    async def create(self, ctx):
        """
        Create a backup


        __Examples__

        ```{b.prefix}backup create```
        """
        status_msg = await ctx.f_send("**Creating Backup** ...", f=ctx.f.WORKING)

        guild = await ctx.get_guild()
        data = guild.to_dict()
        backup_id = data["_id"] = make_id()
        await ctx.bot.db.backups.insert_one(data)

        embed = ctx.f.format(f"Successfully **created backup** with the id `{backup_id}`.", f=ctx.f.SUCCESS)["embed"]
        embed.setdefault("fields", []).append({
            "name": "Usage",
            "value": f"```{ctx.bot.prefix}backup load {backup_id}```\n"
                     f"```{ctx.bot.prefix}backup info {backup_id}```"
        })
        await ctx.edit(status_msg["id"], embed=embed)

    @backup.command()
    async def load(self, ctx):
        """
        Load a backup


        __Arguments__

        **backup_id**: The id of the backup or the guild id of the latest automated backup
        **options**: A list of options (See examples)


        __Examples__

        Default options: ```{b.prefix}backup load oj1xky11871fzrbu```
        Only roles: ```{b.prefix}backup load oj1xky11871fzrbu !* roles```
        Everything but bans: ```{b.prefix}backup load oj1xky11871fzrbu !bans```
        """

    @backup.command()
    async def delete(self, ctx):
        pass

    @backup.command()
    async def purge(self, ctx):
        pass

    @backup.command()
    async def list(self, ctx):
        pass

    @backup.command()
    async def info(self, ctx):
        pass
