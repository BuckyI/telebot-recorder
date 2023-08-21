import logging
from functools import partial
from pathlib import Path
from typing import Callable, List, NamedTuple

import telebot
from decouple import config
from telebot.custom_filters import StateFilter
from telebot.types import CallbackQuery, InputFile, Message
from telebot.util import extract_arguments, extract_command, quick_markup
from telegram_text import Bold, Chain, PlainText, Underline

from ..states.base import ComStates, StepState, StepStatesGroup
from .storage import DataBase

Record = NamedTuple("Record", [("table", str), ("data", dict)])


class Recorder:
    def __init__(self, bot: telebot.TeleBot, db: DataBase) -> None:
        self.bot = bot
        self.db = db
        self.state_group: List[StepStatesGroup] = []

    def register(self, cfg_path: str):
        for group_cfg in StepStatesGroup.validated_configs(cfg_path):
            group = StepStatesGroup(group_cfg)
            self.state_group.append(group)
            logging.info("group registered: %s", group.name)

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
        msg = Chain(
            Bold("Start a New Record:"),
            PlainText(entry_state.group.description),
            sep="\n",
        )
        self.bot.send_message(message.chat.id, msg.to_markdown(), parse_mode="Markdown")
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
            final = current_state.group.get_data(data)
            final["timestamp"] = message.date  # add time of record
            self.__confirm_and_save(
                message.chat.id,
                message.from_user.id,
                Record(current_state.group.name, final),
            )

    def __default(self, message: Message, default_table: str = "records"):
        "default record behavior if no specific state is set"
        bot: telebot.TeleBot = self.bot
        bot.set_state(message.from_user.id, ComStates.save, message.chat.id)
        record = Record(
            default_table,
            {
                "timestamp": message.date,
                "content": message.text,
            },
        )
        self.__confirm_and_save(message.chat.id, message.from_user.id, record)

    def __confirm_and_save(self, chat_id: int, user_id: int, data: Record):
        """
        chat_id: comfirm in this chat
        table: table to insert data
        data: the dict like data to save
        """
        bot: telebot.TeleBot = self.bot
        # save data tempororily
        save_state = ComStates.save
        bot.set_state(user_id, save_state, chat_id)
        with bot.retrieve_data(user_id, chat_id) as user_data:
            user_data[save_state.name] = data  # use name to store data
        # send confirm message
        markup = quick_markup(
            {
                "OK 😇": {"callback_data": "save"},
                "No ❗": {"callback_data": "drop"},
            }
        )
        bot.send_message(chat_id, f"Confirm whether to record", reply_markup=markup)

        def callback(query: CallbackQuery):
            chat_id, user_id, message_id = (
                query.message.chat.id,
                query.from_user.id,
                query.message.message_id,
            )
            if query.data == "save":
                with bot.retrieve_data(user_id, chat_id) as user_data:
                    record: Record = user_data[save_state.name]
                    doc_id = self.db.insert(record.data, record.table)
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
