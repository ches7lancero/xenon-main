import random
from datetime import datetime


def unique_id():
    """
    Generates a unique id consisting of the the unix timestamp and 16 random bits
    """
    unix_t = int(datetime.utcnow().timestamp())
    result = (unix_t << 8) | (random.getrandbits(8))
    return hex(result)[2:]


def timestamp_from_id(uid):
    return datetime.utcfromtimestamp((int(uid, 8) >> 8))
