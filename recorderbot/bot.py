import logging
import os
import time
from typing import Final

import telebot
from decouple import config
from telebot.types import Message
from telebot.util import extract_arguments, extract_command, quick_markup
from telegram_text import Bold, Chain, Code, PlainText, TOMLSection, UnorderedList

from .components import DataBase
from .utils import load_yaml, readable_time

BOT_TOKEN: Final = config("BOT_TOKEN", default="")
BOT_USERNAME: Final = config("BOT_USERNAME", default="")
DATABASE: Final = config("DATABASE", default="botdb.json")


class Bot:
    def __init__(
        self, config: str, bot_name: str = BOT_USERNAME, bot_token: str = BOT_TOKEN
    ) -> None:
        """
        config: path to yaml config path
        bot_name: bot username
        bot_token: bot token
        """
        assert bot_name and bot_token, "Bot name and token are required"
        self.bot = telebot.TeleBot(bot_token)
        self.cfg = load_yaml(config)
        self.storage = DataBase(self.bot, self.cfg["database"]["path"])

    def register(self):
        "register some common commands"
        bot: telebot.TeleBot = self.bot
        bot.register_message_handler(self.__command_start, commands=["start"])
        bot.register_message_handler(timestamp, commands=["timestamp"], pass_bot=True)
        self.storage.register_commands()

    def run(self):
        # initialize database, restore data from webdav backup
        self.storage.restore()
        logging.info("Start Polling...")
        self.bot.infinity_polling()

    def stop(self):
        self.bot.stop_bot()

    def __command_start(self, message: Message):
        "the beginning of everything... clear states"
        bot: telebot.TeleBot = self.bot
        user_id, chat_id = message.from_user.id, message.chat.id

        storage_status = self.storage.status.items()
        storage_status = [Bold(k) + PlainText(f": {v}") for k, v in storage_status]
        section_database = TOMLSection("all records", UnorderedList(*storage_status))

        state: str | None = bot.get_state(user_id, chat_id)
        bot.delete_state(user_id, chat_id)
        section_state = TOMLSection("previous state", PlainText(str(state)))

        commands = set()
        for handler in bot.message_handlers:
            if cmds := handler.get("filters", {}).get("commands"):
                commands = commands.union(cmds)
        commands = [Code(f"/{cmd}") for cmd in commands]
        section_cmd = TOMLSection("avaliable commands", UnorderedList(*commands))

        msg = Chain(
            PlainText("Hello, how are you doing?"),
            section_database,
            section_cmd,
            section_state,
            sep="\n\n",
        )
        bot.send_message(message.chat.id, msg.to_markdown(), parse_mode="MarkdownV2")


def timestamp(message: telebot.types.Message, bot: telebot.TeleBot):
    if reply := message.reply_to_message:
        time = reply.date
        msg = readable_time(time) + ": " + Code(str(time))
    else:
        msg = Bold(
            "You have to reply to a message and call this command to get its timestamp!"
        )
    bot.send_message(message.chat.id, msg.to_markdown(), parse_mode="MarkdownV2")
