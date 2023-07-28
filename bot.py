import os
import time
from pprint import pprint
from typing import Final

import telebot
from decouple import config
from telebot.util import extract_arguments, extract_command, quick_markup

from recorder import Recorder, RecordItem

BOT_TOKEN: Final = config("BOT_TOKEN", default="")
BOT_USERNAME: Final = config("BOT_USERNAME", default="")
HTTPS_PROXY: Final = config("HTTPS_PROXY", default="")
DATABASE: Final = config("DATABASE", default="botdb.json")

bot = telebot.TeleBot(BOT_TOKEN)
recorder = Recorder(DATABASE)


@bot.message_handler(commands=["start"])
def send_welcome(message):
    bot.send_message(message.chat.id, "Hello, how are you doing?")


@bot.message_handler(commands=["search"])
def search_record(message):
    """Two ways to search:
    1. "/search <keywords>"
    2. "/search" and reply "<keywords>"
    """
    command = extract_command(message.text)
    args = extract_arguments(message.text) if command else message.text
    if command and not args:
        bot.send_message(message.chat.id, "Give me a string to search 🤖")
        bot.register_next_step_handler(message, search_record)
        return
    for item in recorder.search(args):
        bot.send_message(message.chat.id, item.to_str())
    bot.send_message(message.chat.id, "Done.")


@bot.message_handler(func=lambda msg: True)
def record(message):
    markup = quick_markup(
        {
            "OK 😇": {"callback_data": "save record"},
            "No ❗": {"callback_data": "drop record"},
        }
    )
    bot.reply_to(message, f"Confirm whether to record", reply_markup=markup)

    def record_callback(query: telebot.types.CallbackQuery):
        chat_id, message_id = query.message.chat.id, query.message.message_id
        if query.data == "save record":
            # the markup will be deleted automatically
            # bot.edit_message_reply_markup(chat_id, message_id)
            message = query.message.reply_to_message  # point to the message to be saved
            doc_id = recorder.record(RecordItem(message.date, message.text))
            bot.edit_message_text(f"Record saved. ({doc_id})", chat_id, message_id)
        elif query.data == "drop record":
            bot.edit_message_text("This message is deprecated.", chat_id, message_id)

    bot.register_callback_query_handler(
        record_callback,
        lambda query: query.data in ["save record", "drop record"],
    )


# TODO: ADD TAGS
# TODO: HOSTING ON A WEB SERVER


def start_polling():
    if HTTPS_PROXY:
        os.environ["https_proxy"] = HTTPS_PROXY
    print("Polling...")
    bot.infinity_polling()


# Run the program
if __name__ == "__main__":
    start_polling()
