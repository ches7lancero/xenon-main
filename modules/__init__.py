from .help import Help
from .admin import Admin
from .backups import Backups
from .templates import Templates
from .basics import Basics
from .redis import Redis
from .blacklist import Blacklist
from .sync import Sync
from .copy import Copy
from .chatlog import Chatlog


to_load = (Help, Admin, Backups, Basics, Templates, Build, Redis, Blacklist, Sync, Copy, Chatlog)
