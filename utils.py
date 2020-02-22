import random
from datetime import datetime
import discord_worker as wkr


base36 = '0123456789abcdefghijklmnopqrstuvwxyz'


def base36_dumps(number: int):
    if number < 0:
        return '-' + base36_dumps(-number)

    value = ''

    while number != 0:
        number, index = divmod(number, len(base36))
        value = base36[index] + value

    return value or '0'


def base36_loads(value):
    return int(value, len(base36))


def unique_id():
    """
    Generates a unique id consisting of the the unix timestamp and 8 random bits
    """
    unix_t = int(datetime.utcnow().timestamp() * 1000)
    result = (unix_t << 8) | random.getrandbits(8)
    return base36_dumps(result)


def timestamp_from_id(uid):
    return datetime.utcfromtimestamp((base36_loads(uid) >> 8) / 1000)


def datetime_to_string(datetime):
    return datetime.strftime("%d. %b %Y - %H:%M")


class IterWaitFor:
    def __init__(self, client, *args, **kwargs):
        self.client = client
        self.args = args
        self.kwargs = kwargs

    def __aiter__(self):
        return self

    async def __anext__(self):
        return await self.client.wait_for(*self.args, **self.kwargs)


def channel_tree(channels):
    text = []
    voice = []
    ctg = []

    for channel in sorted(channels, key=lambda c: c.position):
        if channel.type == wkr.ChannelType.GUILD_VOICE:
            voice.append(channel)

        elif channel.type == wkr.ChannelType.GUILD_CATEGORY:
            ctg.append(channel)

        else:
            text.append(channel)

    result = "```"
    text_no_ctg = filter(lambda t: t.parent_id is None, text)
    for channel in text_no_ctg:
        result += "\n#\u200a" + channel.name

    voice_no_ctg = filter(lambda v: v.parent_id is None, voice)
    for channel in voice_no_ctg:
        result += "\n<\u200a" + channel.name

    result += "\n"

    for category in ctg:
        result += "\n°\u200a" + category.name
        t_children = filter(lambda c: c.parent_id == category.id, text)
        for channel in t_children:
            result += "\n  #\u200a" + channel.name

        v_children = filter(lambda c: c.parent_id == category.id, voice)
        for channel in v_children:
            result += "\n  <\u200a" + channel.name

        result += "\n"

    return result + "```"
