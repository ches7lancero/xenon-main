import traceback
import xenon_worker as wkr
import asyncio


class Options:
    def __init__(self, **default):
        self.all = False
        self.options = default

    def update(self, **options):
        for key, value in options.items():
            if key == "*":
                self.all = value
                self.options.clear()

            else:
                self.options[key] = value

    def __getattr__(self, item):
        return self.get(item)

    def get(self, item):
        if item in self.options.keys():
            return bool(self.options[item])

        return self.all


class BackupSaver:
    def __init__(self, client, guild):
        self.client = client
        self.guild = guild
        self.data = guild.to_dict()
        self.chatlog = None

    async def _save_roles(self):
        self.data["roles"] = [
            r.to_dict()
            for r in self.guild.roles
            if not r.managed
        ]

    async def _save_bans(self):
        self.data["bans"] = [
            {
                "reason": ban["reason"],
                "id": ban["user"]["id"]
            }
            for ban in await self.client.fetch_bans(self.guild)
        ]

    async def _save_members(self):
        self.data["members"] = [
            {
                "id": member.id,
                "nick": member.nick,
                "deaf": member.deaf,
                "mute": member.mute,
                "roles": member.roles
            }
            async for member in self.client.iter_members(self.guild, 10 ** 6)
        ]

    async def _save_messages(self):
        if self.chatlog <= 0:
            return

        messages = self.data["messages"] = {}

        for channel in self.guild.channels:
            messages[channel.id] = [
                {
                    "id": message.id,
                    "content": message.content,
                    "author": message.author.user.to_dict(),
                    "attachments": [
                        {
                            "filename": attachment["filename"],
                            "url": attachment["url"]
                        }
                        for attachment in message.attachments
                    ],
                    "pinned": message.pinned,
                    "embeds": message.embeds
                }
                async for message in self.client.iter_messages(channel, self.chatlog)
            ]

    async def save(self, chatlog=0, **options):
        self.chatlog = chatlog
        savers = {
            "roles": self._save_roles,
            "bans": self._save_bans,
            "members": self._save_members,
            "messages": self._save_messages
        }

        for _, saver in savers.items():
            await saver()


class BackupLoader:
    def __init__(self, client, guild, data, reason="Backup loaded"):
        self.client = client
        self.guild = guild
        self.data = data

        self.chatlog = None
        self.options = Options(
            settings=True,
            roles=True,
            delete_roles=True,
            channels=True,
            delete_channels=True,
            bans=True,
            members=True
        )
        self.id_translator = {}
        self.reason = reason

        self._member_cache = {}

    async def _load_settings(self):
        self.data.pop("guild_id", None)
        await self.client.edit_guild(self.guild, **self.data, reason=self.reason)

    async def _clean_members(self):
        async for member in self.client.iter_members(self.guild, 10 ** 6):
            roles = [r.id for r in member.roles_from_guild(self.guild) if r.managed]
            self._member_cache[member.id] = roles
            try:
                await self.client.edit_member(self.guild, member, roles=roles)
            except Exception:
                pass

    async def _load_roles(self):
        bot_member = await self.client.get_bot_member(self.guild.id)
        top_role = list(sorted(bot_member.roles_from_guild(self.guild), key=lambda r: r.position))[-1]

        existing = sorted(
            [r for r in filter(
                lambda r: not r.managed and not r.is_default() and r.position < top_role.position,
                self.guild.roles
            )],
            key=lambda r: r.position,
            reverse=True
        )
        remaining = list(sorted(self.data["roles"], key=lambda r: r["position"], reverse=True))
        for role in remaining:
            role.pop("guild_id", None)

            # Default role (@everyone)
            if role["position"] == 0:
                to_edit = self.guild.default_role
                if to_edit is not None:
                    try:
                        await self.client.edit_role(to_edit, **role, reason=self.reason)
                        self.id_translator[role["id"]] = to_edit.id

                    except Exception:
                        traceback.print_exc()

                continue

            if len(existing) > 0:
                try:
                    to_edit = existing.pop(0)
                    await self.client.edit_role(to_edit, **role, reason=self.reason)
                    self.id_translator[role["id"]] = to_edit.id
                    continue
                except Exception:
                    traceback.print_exc()

            try:
                new = await asyncio.wait_for(
                    self.client.create_role(self.guild, **role, reason=self.reason),
                    timeout=15
                )
            except asyncio.TimeoutError:
                raise self.client.f.ERROR("Seems like you **hit** the `250 per 24h` **role creation limit** of "
                                          "discord.\nYou can either **wait 24 hours** until the limit was reset or "
                                          "create enough roles manually for Xenon to use. This way, Xenon does not "
                                          "need to create new roles, but can edit the existing ones.")

            self.id_translator[role["id"]] = new.id

        for role in existing:
            await self.client.delete_role(role, reason=self.reason)

    async def _delete_channels(self):
        for channel in self.guild.channels:
            try:
                await self.client.delete_channel(channel, reason=self.reason)
            except:
                traceback.print_exc()

    async def _load_channels(self):
        def _tune_channel(channel):
            channel.pop("guild_id", None)

            # Bitrates over 96000 require special features or boosts
            # (boost advantages change a lot, so we just ignore them)
            if "bitrate" in channel.keys() and "VIP_REGIONS" not in self.guild.features:
                channel["bitrate"] = min(channel["bitrate"], 96000)

            # News and store channels require special features
            if (channel["type"] == wkr.ChannelType.GUILD_NEWS and "NEWS" not in self.guild.features) or \
                    (channel["type"] == wkr.ChannelType.GUILD_STORE and "COMMERCE" not in self.guild.features):
                channel["type"] = 0

            channel["type"] = 0 if channel["type"] > 4 else channel["type"]

            if "parent_id" in channel.keys():
                channel["parent_id"] = self.id_translator.get(channel["parent_id"], channel["parent_id"])

            overwrites = channel.get("permission_overwrites", [])
            for overwrite in overwrites:
                overwrite["id"] = self.id_translator.get(overwrite["id"], overwrite["id"])

            return channel

        no_parent = sorted(
            filter(lambda c: c.get("parent_id") is None, self.data["channels"]),
            key=lambda c: c.get("position")
        )
        for channel in no_parent:
            new = await self.client.create_channel(self.guild, **_tune_channel(channel), reason=self.reason)
            self.id_translator[channel["id"]] = new.id

        has_parent = sorted(
            filter(lambda c: c.get("parent_id") is not None, self.data["channels"]),
            key=lambda c: c["position"]
        )
        for channel in has_parent:
            new = await self.client.create_channel(self.guild, **_tune_channel(channel), reason=self.reason)
            self.id_translator[channel["id"]] = new.id

    async def _load_bans(self):
        for ban in self.data.get("bans", []):
            try:
                await self.client.ban_user(self.guild, wkr.Snowflake(ban["id"]), reason=ban["reason"])
            except Exception:
                pass

    async def _load_members(self):
        for member in self.data.get("members", []):
            roles = self._member_cache.get(member["id"])
            if roles is None:
                continue

            for role in member["roles"]:
                new_id = self.id_translator.get(role)
                if new_id is not None:
                    roles.append(new_id)

            try:
                await self.client.edit_member(
                    self.guild,
                    wkr.Snowflake(member["id"]),
                    nick=member.get("nick"),
                    roles=roles
                )
            except Exception:
                pass

    async def _load_messages(self):
        async def _load_in_channel(channel):
            messages = self.data.get("messages", {}).get(channel["id"], [])
            if len(messages) <= 0:
                return

            new_id = self.id_translator.get(channel["id"])
            if new_id is None:
                return

            webhook = await self.client.create_webhook(wkr.Snowflake(new_id), name="backup")
            for msg in reversed(messages[:self.chatlog]):
                author = wkr.User(msg["author"])
                try:
                    await self.client.execute_webhook(
                        webhook,
                        wait=True,
                        username=author.name,
                        avatar_url=author.avatar_url,
                        **msg
                    )
                except wkr.NotFound:
                    break

                except Exception:
                    pass

            await self.client.delete_webhook(webhook)

        for _channel in self.data["channels"]:
            self.client.schedule(_load_in_channel(_channel))

    async def load(self, chatlog, **options):
        self.chatlog = chatlog
        self.options.update(**options)
        await self.client.edit_guild(self.guild, name="Loading ...")
        loaders = (
            ("delete_roles", self._clean_members),
            ("roles", self._load_roles),
            ("delete_channels", self._delete_channels),
            ("channels", self._load_channels),
            ("bans", self._load_bans),
            ("members", self._load_members),
            ("channels", self._load_messages)
        )

        for key, loader in loaders:
            if self.options.get(key):
                try:
                    await loader()
                except wkr.CommandError:
                    raise
                except Exception:
                    traceback.print_exc()
