import logging
import os
import time
from typing import Final

import telebot
from decouple import config
from telebot.types import InputFile
from telebot.util import extract_arguments, extract_command, quick_markup

from .authenticate import Authenticator
from .storage import DataBase
from .utils import is_small_file, save_file

BOT_TOKEN: Final = config("BOT_TOKEN", default="")
BOT_USERNAME: Final = config("BOT_USERNAME", default="")
DATABASE: Final = config("DATABASE", default="botdb.json")

bot = telebot.TeleBot(BOT_TOKEN)
storage = DataBase(DATABASE)


## first level commands


@bot.message_handler(commands=["start"])
def send_welcome(message):
    msg = f"Hello, how are you doing?\n{storage.status}"
    bot.send_message(message.chat.id, msg)


@bot.message_handler(commands=["debug"])
def debug(message):
    bot.send_message(message.chat.id, str(message))


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
                f"updated {num} item(s) successfully 😃, status: {storage.status}",
                msg.chat.id,
                msg.message_id,
            )

        bot.register_next_step_handler(query.message, save_file_from_message)

    def restore_from_webdav(query):
        chat_id, message_id = query.message.chat.id, query.message.message_id
        bot.edit_message_text("in processing... 🤖", chat_id, message_id)
        num = storage.restore()
        bot.edit_message_text(
            f"updated {num} item(s) successfully 😃, status: {storage.status}",
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
