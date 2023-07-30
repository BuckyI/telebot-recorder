import logging
import os
from typing import Final

from decouple import config

import recorderbot
from recorderbot.bot import bot, recorder

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    HTTPS_PROXY: Final = config("HTTPS_PROXY", default="")
    if HTTPS_PROXY:
        os.environ["https_proxy"] = HTTPS_PROXY
    num = recorder.merge_from_backup()
    logging.info("Retrieve {} record(s) from backup.".format(num))
    logging.info("Start Polling...")
    bot.infinity_polling()
