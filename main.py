import logging
import os
from typing import Final

from decouple import config

from recorderbot.bot import bot, storage

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    HTTPS_PROXY: Final = config("HTTPS_PROXY", default="")
    if HTTPS_PROXY:
        os.environ["https_proxy"] = HTTPS_PROXY
    # initialize database, restore data from webdav backup
    storage.restore()
    logging.info("Start Polling...")
    bot.infinity_polling()
