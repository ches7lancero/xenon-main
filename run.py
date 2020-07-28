from bot import Xenon
from os import environ as env


bot = Xenon(
    prefix=env.get("PREFIX") or "#!",
    mongo_url=env.get("MONGO_URL") or "mongodb://localhost",
    rabbit_url=env.get("RABBIT_URL") or "amqp://guest:guest@localhost/",
    redis_url=env.get("REDIS_URL") or "redis://localhost/"
)
bot.run(token=env.get("NzM3NTY0Nzg3MDI1NjQxNTMz.Xx_MvA.UELHQ9-FCFi1mY2IhmZVNnZGstE"), shared_queue="main")
