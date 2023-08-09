from functools import partial

import telebot  # telebot
from telebot import custom_filters
from telebot.handler_backends import State, StatesGroup  # States
from telebot.storage import StateMemoryStorage  # States storage

from .base import StepState, get_text


class StepStatesGroup(StatesGroup):
    # Just name variables differently
    name = StepState("1. Please enter Your name", "name")
    surname = StepState("2. Please enter Your surname", "surname")
    age = StepState("3. Please enter Your age", "age")

    states = [name, surname, age]
    name.next = surname
    surname.next = age

    @classmethod
    def get_entry_state(cls) -> StepState:
        return cls.states[0]

    @classmethod
    def get_last_state(cls) -> StepState:
        return cls.states[-1]

    @classmethod
    def register(cls, bot: telebot.TeleBot):
        for s in cls.states:  #  when it is finished, save data
            bot.register_message_handler(
                partial(get_text, current_state=s, bot=bot, callback=cls.save_data),
                state=s,
            )

    @classmethod
    def get_data(cls, raw_data: dict) -> dict:
        "extract data belong to this states group"
        return {state.key: raw_data.get(state.name, "") for state in cls.states}

    @classmethod
    def save_data(cls, data: dict) -> str:
        """the final process to process full data
        data: the full data (should be given in outter procedures)
        return: human readable information of process result
        """
        # TODO: not implemented, maybe use cached data
        with open("temp_save_states.txt", "a+") as f:
            f.write(str(data) + "\n")


def initialize(command: str, bot: telebot.TeleBot):
    "setup states group"

    def start(message):
        start = StepStatesGroup.get_entry_state()
        bot.set_state(message.from_user.id, start, message.chat.id)
        bot.send_message(message.chat.id, start.hint)

    bot.register_message_handler(start, commands=[command])
    StepStatesGroup.register(bot)
    bot.add_custom_filter(custom_filters.StateFilter(bot))
    return StepStatesGroup
