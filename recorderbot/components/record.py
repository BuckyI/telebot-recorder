import logging
from functools import partial
from pathlib import Path
from typing import Callable, List

import telebot
from decouple import config
from telebot.custom_filters import StateFilter
from telebot.types import CallbackQuery, InputFile, Message
from telebot.util import extract_arguments, extract_command, quick_markup

from ..states.base import ComStates, StepState, StepStatesGroup
from .storage import DataBase


class Recorder:
    def __init__(self, bot: telebot.TeleBot, db: DataBase) -> None:
        self.bot = bot
        self.db = db
        self.state_group: List[StepStatesGroup] = []

    def register(self, group_configs: List[str]):
        groups = [StepStatesGroup(cfg) for cfg in group_configs]
        # update state_groups
        self.state_group.extend(groups)
        logging.info("groups registered: %s", [str(g) for g in self.state_group])

        # register commands first so you can change states in middle states
        for sg in self.state_group:
            self.register_command(sg)
        for sg in self.state_group:
            self.register_states(sg)

        # By default, save to "records" table if no state is specified
        self.bot.register_message_handler(self.__default)
        self.state_group.append("records")

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
                bot.set_state(message.from_user.id, ComStates.save, message.chat.id)
                final = current_state.group.get_data(data)
                final["timestamp"] = message.date  # add time of record
                self.__confirm_and_save(
                    message.chat.id, current_state.group.name, final
                )

    def __default(self, message: Message, default_table: str = "records"):
        "default record behavior if no specific state is set"
        bot: telebot.TeleBot = self.bot
        bot.set_state(message.from_user.id, ComStates.save, message.chat.id)
        # save final data temporarily
        final = {"timestamp": message.date, "content": message.text}
        self.__confirm_and_save(message.chat.id, default_table, final)

    def __confirm_and_save(self, chat_id: int, table: str, data: dict):
        """
        chat_id: comfirm in this chat
        table: table to insert data
        data: the dict like data to save
        """
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
                doc_id = self.db.insert(data, table)
                self.db.backup()  # backup to webdav
                logging.info("backup after new record added via webdav")
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
