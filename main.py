import logging
import os
from typing import Final

from decouple import config

from recorderbot.bot import Bot
from recorderbot.components import Authenticator, Recorder

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    HTTPS_PROXY: Final = config("HTTPS_PROXY", default="")
    if HTTPS_PROXY:
        os.environ["https_proxy"] = HTTPS_PROXY

    bot = Bot("configs/bot.yaml")

    # register message handlers
    bot.register()
    auth = Authenticator(bot.bot, bot.storage)
    auth.register_command("register")
    recorder = Recorder(bot.bot, bot.storage)
    recorder.register("configs/templates/")
    # WARNING: recorder 会接收所有 text 类型的消息，不要在此之后 register

    bot.run()
