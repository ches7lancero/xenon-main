import xenon_worker as wkr

import checks
import utils
from backups import BackupSaver, BackupLoader


class Copy(wkr.Module):
    @wkr.Module.command(hidden=True)
    @wkr.guild_only
    @wkr.has_permissions(administrator=True)
    @wkr.bot_has_permissions(administrator=True)
    @checks.is_premium()
    @wkr.cooldown(1, 60, bucket=wkr.CooldownType.GUILD)
    async def copy(self, ctx, guild_id: wkr.FullGuildConverter, chatlog: int = 0, *options):
        """
        Copy a server without creating a backup


        **guild_id**: The id of the guild to copy from
        **chatlog**: The count of messages to copy per channel
        """
        source_guild = await guild_id(ctx)
        target_guild = await ctx.get_full_guild()

        bot_member = await ctx.client.get_bot_member(source_guild.id)
        if bot_member is None:
            raise wkr.BotMissingPermissions(("administrator",))

        permissions = bot_member.permissions_for_guild(source_guild)
        if not permissions.administrator:
            raise wkr.BotMissingPermissions(("administrator",))

        if ctx.premium == checks.PremiumLevel.ONE:
            chatlog = min(chatlog, 50)

        elif ctx.premium == checks.PremiumLevel.TWO:
            chatlog = min(chatlog, 100)

        elif ctx.premium == checks.PremiumLevel.THREE:
            chatlog = min(chatlog, 250)

        status_msg = await ctx.f_send("**Preparing to copy** ...", f=ctx.f.WORKING)
        backup = BackupSaver(ctx.client, source_guild)
        await backup.save(chatlog)

        await ctx.client.edit_message(status_msg, **ctx.f.format(f"**Starting to copy** ...", f=ctx.f.WORKING))

        loader = BackupLoader(ctx.client, target_guild, backup.data, reason="Copied by " + str(ctx.author))
        await loader.load(chatlog, **utils.backup_options(options))

    @copy.command(aliases=('msg',))
    @wkr.guild_only
    @wkr.has_permissions(administrator=True)
    @wkr.bot_has_permissions(administrator=True)
    @checks.is_premium()
    @wkr.cooldown(1, 60, bucket=wkr.CooldownType.GUILD)
    async def messages(self, ctx, channel_id: wkr.ChannelConverter, count: int = 100):
        """
        Copy messages from one channel to another without creating a chatlog


        **channel_id**: The id of the channel to copy from
        **count**: The count of messages to copy
        """
        channel = await channel_id(ctx)
