from discord_worker import RabbitBot
import modules


class Xenon(RabbitBot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db = self.mongo.xenon
        for module in modules.to_load:
            self.add_module(module(self))
