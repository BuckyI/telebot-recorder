from functools import partial
from typing import Final

import telebot  # telebot
from decouple import config
from telebot import custom_filters

from recorderbot.states.userinfo import StepStatesGroup, initialize


def test_userinfo():
    BOT_TOKEN: Final = config("BOT_TOKEN", default="")
    BOT_USERNAME: Final = config("BOT_USERNAME", default="")
    bot = telebot.TeleBot(BOT_TOKEN)
    initialize("start", bot)
    bot.infinity_polling(skip_pending=True)
