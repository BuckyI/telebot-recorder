import logging
import os
import time
from typing import Final

import telebot
from decouple import config
from telebot.types import InputFile
from telebot.util import extract_arguments, extract_command, quick_markup

from .authenticate import Authenticator
from .recorder import Recorder, RecordItem
from .storage import DataBase
from .utils import is_small_file, save_file

BOT_TOKEN: Final = config("BOT_TOKEN", default="")
BOT_USERNAME: Final = config("BOT_USERNAME", default="")
DATABASE: Final = config("DATABASE", default="botdb.json")

bot = telebot.TeleBot(BOT_TOKEN)
storage = DataBase(DATABASE)
recorder = Recorder(DATABASE)
auth = Authenticator(DATABASE)


@bot.message_handler(commands=["start"])
def send_welcome(message):
    msg = (
        f"Hello, how are you doing?\n" f"You have recorded {recorder.size} messages!\n"
    )
    bot.send_message(message.chat.id, msg)


@bot.message_handler(commands=["debug"])
def debug(message):
    bot.send_message(message.chat.id, str(message))


@bot.message_handler(commands=["register"])
def register(message):
    if auth.is_registered(message.chat.id):
        bot.send_message(message.chat.id, "You have already registered 🤖")
    else:
        auth.register(message.chat.id)
        bot.send_message(message.chat.id, "Registered successfully 🎉")
        storage.backup()


@bot.message_handler(commands=["backup"])
def backup(message):
    # TODO: Get file ID
    if not is_small_file(DATABASE):
        bot.send_message(message.chat.id, "Database is too big to backup 👀")
    bot.send_document(message.chat.id, InputFile(DATABASE), caption="Backup")


@bot.message_handler(commands=["restore"])
def restore(message):
    """
    select how to restore -->
    - from file --> upload a file --> restore
    - from webdav --> restore
    """
    # TODO: simplify it
    markup = quick_markup(
        {
            "Upload a file 📄": {"callback_data": "restore file"},
            "From WebDAV 📥": {"callback_data": "restore webdav"},
        }
    )
    bot.reply_to(message, f"Confirm how to restore 👀", reply_markup=markup)

    def restore_from_file(query):
        chat_id, message_id = query.message.chat.id, query.message.message_id
        bot.edit_message_text("Give me a document to restore 🤖", chat_id, message_id)

        def save_file_from_message(message):
            if message.content_type != "document":
                bot.send_message(message.chat.id, "You have to upload a file 🤖")
                return

            url = bot.get_file_url(message.document.file_id)
            save_file(url, "temp.json")
            msg = bot.send_message(message.chat.id, f"Received, in processing...")
            num = storage.restore("temp.json")
            bot.edit_message_text(
                f"updated {num} item(s) successfully 😃, total records: {recorder.size}",
                msg.chat.id,
                msg.message_id,
            )

        bot.register_next_step_handler(query.message, save_file_from_message)

    def restore_from_webdav(query):
        chat_id, message_id = query.message.chat.id, query.message.message_id
        bot.edit_message_text("in processing... 🤖", chat_id, message_id)
        num = storage.restore()
        bot.edit_message_text(
            f"updated {num} item(s) successfully 😃, total records: {recorder.size}",
            chat_id,
            message_id,
        )

    bot.register_callback_query_handler(
        restore_from_file,
        lambda query: query.data == "restore file",
    )
    bot.register_callback_query_handler(
        restore_from_webdav,
        lambda query: query.data == "restore webdav",
    )


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
            storage.backup()
            logging.info("backup after new record added via webdav")
            bot.edit_message_text(f"Record saved. ({doc_id})", chat_id, message_id)
        elif query.data == "drop record":
            bot.edit_message_text("This message is deprecated.", chat_id, message_id)

    bot.register_callback_query_handler(
        record_callback,
        lambda query: query.data in ["save record", "drop record"],
    )


# TODO: ADD TAGS
# TODO: HOSTING ON A WEB SERVER


# Handle all other messages.
@bot.message_handler(
    func=lambda message: True,
    content_types=[
        "audio",
        "photo",
        "voice",
        "video",
        "document",
        "text",
        "location",
        "contact",
        "sticker",
    ],
)
def catch_all(message):
    bot.reply_to(message, "This message type is not supported.")
