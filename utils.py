import random
from datetime import datetime


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
