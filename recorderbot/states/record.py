import logging
from functools import partial
from pathlib import Path
from typing import Callable, List

import telebot
from decouple import config
from telebot.custom_filters import StateFilter
from telebot.handler_backends import State, StatesGroup
from telebot.types import CallbackQuery, InputFile, Message
from telebot.util import extract_arguments, extract_command, quick_markup

from ..storage import DataBase
from .base import ComStates, StepState, StepStatesGroup


class Recorder:
    def __init__(
        self, bot: telebot.TeleBot, db: DataBase, states: List[StepStatesGroup]
    ) -> None:
        self.bot = bot
        self.db = db
        self.state_group: List[StepStatesGroup] = []
        self.register(states)

    def register(self, state_groups: List[StepStatesGroup]):
        self.state_group.extend(state_groups)  # update state_groups
        # register commands first so you can change states in middle states
        for sg in self.state_group:
            self.register_command(sg)
        for sg in self.state_group:
            self.register_states(sg)

        self.bot.add_custom_filter(StateFilter(self.bot))

    def register_command(self, state_group: StepStatesGroup):
        "make sure command is registered first"
        assert state_group.command, "no valid command is given"
        self.bot.register_message_handler(
            partial(self.__enter, entry_state=state_group.entry_state),
            commands=[state_group.command],
        )

    def register_states(self, state_group: StepStatesGroup):
        """setup states group, register message handlers to bot
        bot: the telebot instance to register handlers
        command: the command to enter this states group, default to None,
        which will try to get `cls.command` from definition.
        """
        for s in state_group.state_list:
            self.bot.register_message_handler(
                partial(self.__move_on, current_state=s),
                state=s,
            )
        return state_group

    def __enter(self, message: Message, entry_state: StepState):
        self.bot.set_state(message.from_user.id, entry_state, message.chat.id)
        self.bot.send_message(message.chat.id, entry_state.hint)

    def __move_on(
        self,
        message: Message,
        current_state: StepState,
    ):
        text: str = message.text
        next_state: StepState = current_state.next
        bot: telebot.TeleBot = self.bot
        # save & retrieve data
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data[current_state.name] = text  # use name to store data
            # move on to next step
            if next_state:
                bot.set_state(message.from_user.id, next_state, message.chat.id)
                bot.send_message(message.chat.id, next_state.hint)
            else:  # all states finished, check & save them
                next_state = ComStates.save
                bot.set_state(message.from_user.id, next_state, message.chat.id)
                # save final data temporarily
                final = current_state.group.get_data(data)
                final["timestamp"] = message.date  # add time of record
                data[next_state.name] = (current_state.group.name, final)
                self.__confirm_and_save(message.chat.id)

    def __confirm_and_save(self, chat_id: int):
        markup = quick_markup(
            {
                "OK 😇": {"callback_data": "save"},
                "No ❗": {"callback_data": "drop"},
            }
        )
        bot: telebot.TeleBot = self.bot
        bot.send_message(chat_id, f"Confirm whether to record", reply_markup=markup)

        def callback(query: CallbackQuery):
            chat_id, user_id, message_id = (
                query.message.chat.id,
                query.from_user.id,
                query.message.message_id,
            )
            if query.data == "save":
                with bot.retrieve_data(user_id, chat_id) as data:
                    table, result = data.get(ComStates.save.name)
                    doc_id = self.db.insert(result, table)
                    self.db.backup()  # backup to webdav
                bot.edit_message_text(f"saved. ({doc_id})", chat_id, message_id)
            else:
                bot.edit_message_text("deprecated.", chat_id, message_id)
            # clear state
            bot.delete_state(user_id, chat_id)

        bot.register_callback_query_handler(
            callback,
            lambda query: query.message.chat.id == chat_id,
            state=ComStates.save,
        )
