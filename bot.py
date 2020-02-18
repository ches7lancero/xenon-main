import discord_worker as wkr
import modules


class Xenon(wkr.RabbitBot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db = self.mongo.xenon
        for module in modules.to_load:
            self.add_module(module(self))
