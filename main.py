import logging
import os

from recorderbot import HTTPS_PROXY, bot, recorder

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    if HTTPS_PROXY:
        os.environ["https_proxy"] = HTTPS_PROXY
    num = recorder.merge_from_backup()
    logging.info("Retrieve {} record(s) from backup.".format(num))
    logging.info("Start Polling...")
    bot.infinity_polling()
