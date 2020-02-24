import discord_worker as wkr


class Basics(wkr.Module):
    @wkr.Module.command()
    @wkr.has_permissions(administrator=True)
    async def leave(self, ctx):
        await ctx.send("bye ;(")
        await ctx.bot.leave_guild(wkr.Snowflake(ctx.guild_id))

    @wkr.Module.command(aliases=["ping", "status"])
    @wkr.cooldown(1, 10)
    async def shards(self, ctx):
        meta = await ctx.bot.cache.shards.find_one({"_id": "meta"})
        if meta is None:
            raise ctx.f.ERROR("Can't fetch shard info.")

        shard_count = meta.get("shard_count", 1)
        latencies = []
        async for shard in ctx.bot.cache.shards.find({
            "_id": {"$ne": "meta", "$lt": shard_count}
        }):
            if shard["latency"] != -1:
                latencies.append(shard["latency"])

        raise ctx.f.INFO(embed={
            "author": {
                "name": "Shard Overview"
            },
            "fields": [
                {
                    "name": "Status",
                    "value": f"{len(latencies)} / {shard_count} online",
                    "inline": True
                },
                {
                    "name": "Average Latency",
                    "value": str(sum(latencies) / len(latencies)),
                    "inline": True
                }
            ]
        })

    @wkr.Module.command(aliases=["iv"])
    @wkr.cooldown(1, 5)
    async def invite(self, ctx):
        invite_url = wkr.invite_url(ctx.bot.user.id, wkr.Permissions(administrator=True))
        raise ctx.f.INFO(f"Click [here]({invite_url}) to **invite {ctx.bot.user.name}** to your server.")

    @wkr.Module.command(aliases=["i"])
    @wkr.cooldown(1, 10)
    async def info(self, ctx):
        app = await ctx.bot.app_info()
        team_members = [app["owner"]["id"]]
        team = app.get("team")
        if team is not None:
            team_members = [tm["user"]["id"] for tm in team["members"]]

        raise ctx.f.INFO(embed={
            "author": {
                "name": ctx.bot.user.name
            },
            "description": "Server Backups, Temapltes and more",
            "fields": [
                {
                    "name": "Invite",
                    "value": f"[Click Here]({wkr.invite_url(ctx.bot.user.id, wkr.Permissions(administrator=True))})",
                    "inline": True
                },
                {
                    "name": "Discord",
                    "value": f"[Click Here](https://discord.club/discord)",
                    "inline": True
                },
                {
                    "name": "Prefix",
                    "value": ctx.bot.prefix,
                    "inline": True
                },
                {
                    "name": "Team",
                    "value": " ".join([f"<@{tm}>" for tm in team_members]),
                    "inline": True
                }
            ]
        })
