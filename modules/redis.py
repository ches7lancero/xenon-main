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
            if isinstance(result, bytes):
                result = msgpack.unpackb(result)

            raise ctx.f.INFO(f"```py\n{result}\n```")

    @cache.command()
    @wkr.is_bot_owner
    async def guild(self, ctx, guild_id):
        result = await ctx.bot.redis.hget("guilds", guild_id)
        data = msgpack.unpackb(result)
        raise ctx.f.INFO(f"```py\n{json.dumps(data, indent=1)}\n```")

    @cache.command()
    @wkr.is_bot_owner
    async def channel(self, ctx, channel_id):
        result = await ctx.bot.redis.hget("channels", channel_id)
        data = msgpack.unpackb(result)
        raise ctx.f.INFO(f"```py\n{json.dumps(data, indent=1)}\n```")

    @cache.command()
    @wkr.is_bot_owner
    async def role(self, ctx, role_id):
        result = await ctx.bot.redis.hget("roles", role_id)
        data = msgpack.unpackb(result)
        raise ctx.f.INFO(f"```py\n{json.dumps(data, indent=1)}\n```")
