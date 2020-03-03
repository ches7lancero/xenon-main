import discord_worker as wkr
import msgpack
import json


class Redis(wkr.Module):
    @wkr.Module.command(hidden=True, aliases=('redis',))
    @wkr.is_bot_owner
    async def cache(self, ctx, *cmd):
        if len(cmd) == 0:
            guild_count = await ctx.bot.redis.hlen("guilds")
            channel_count = await ctx.bot.redis.hlen("channels")
            role_count = await ctx.bot.redis.hlen("roles")
            raise ctx.f.INFO(embed={
                "title": "Cache Stats",
                "fields": [
                    {
                        "name": "Guilds",
                        "value": guild_count,
                        "inline": True
                    },
                    {
                        "name": "Channels",
                        "value": channel_count,
                        "inline": True,
                    },
                    {
                        "name": "Roles",
                        "value": role_count,
                        "inline": True,
                    }
                ]
            })

        else:
            result = await ctx.bot.redis.execute(*cmd)
            raise ctx.f.INFO(f"```py\n{result}\n```")

    @cache.command()
    @wkr.is_bot_owner
    async def guild(self, ctx, guild_id):
        if not await ctx.bot.redis.hexists("guilds", guild_id):
            await ctx.f_send("Guild is not in cache. Fetching and adding ...", f=ctx.f.WORKING)
            try:
                guild = await ctx.bot.fetch_guild(guild_id)
                data = guild.to_dict()
                data.pop("emojis", None)
                data.pop("voice_states", None)
                data.pop("presences", None)
                await ctx.bot.redis.hmset_dict("roles", {r["id"]: msgpack.packb(r) for r in data.pop("roles", [])})
                await ctx.bot.redis.hset("guilds", guild_id, msgpack.packb(data))

            except wkr.NotFound:
                raise ctx.f.ERROR("Guild not found.")

        result = await ctx.bot.redis.hget("guilds", guild_id)
        data = msgpack.unpackb(result)
        raise ctx.f.INFO(f"```js\n{json.dumps(data, indent=1)}\n```")

    @cache.command()
    @wkr.is_bot_owner
    async def channel(self, ctx, channel_id):
        if not await ctx.bot.redis.hexists("channels", channel_id):
            await ctx.f_send("Channel is not in cache. Fetching and adding ...", f=ctx.f.WORKING)
            try:
                channel = await ctx.bot.fetch_channel(channel_id)
                await ctx.bot.redis.hset("channels", channel_id, msgpack.packb(channel.to_dict()))

            except wkr.NotFound:
                raise ctx.f.ERROR("Channel not found.")

        result = await ctx.bot.redis.hget("channels", channel_id)
        data = msgpack.unpackb(result)
        raise ctx.f.INFO(f"```js\n{json.dumps(data, indent=1)}\n```")

    @cache.command()
    @wkr.is_bot_owner
    async def role(self, ctx, role_id, guild_id=None):
        if not await ctx.bot.redis.hexists("roles", role_id):
            if guild_id is None:
                raise ctx.f.ERROR("Role is not in cache. Provide a guild_id to fetch and add it.")

            await ctx.f_send("Role is not in cache. Fetching and adding ...", f=ctx.f.WORKING)
            try:
                roles = await ctx.bot.fetch_roles(wkr.Snowflake(guild_id))
                await ctx.bot.redis.hmset_dict("roles", {r.id: msgpack.packb(r.to_dict()) for r in roles})

            except wkr.NotFound:
                raise ctx.f.ERROR("Role not found.")

        result = await ctx.bot.redis.hget("roles", role_id)
        data = msgpack.unpackb(result)
        raise ctx.f.INFO(f"```js\n{json.dumps(data, indent=1)}\n```")
