from .help import Help
from .admin import Admin
from .backups import Backups
from .templates import Templates
from .basics import Basics
from .build import Build
from .redis import Redis


to_load = (Help, Admin, Backups, Basics, Templates, Build, Redis)
