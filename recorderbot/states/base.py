from functools import partial
from typing import Callable, List

import telebot
from telebot.custom_filters import StateFilter
from telebot.handler_backends import State, StatesGroup

from ..utils import load_yaml


class StepState(State):
    """
    describes linear step states
    name: [predefined] unique name (see StatesGroup)
    group: [predefined] states group it belongs to (see StatesGroup)
    hint: a human readable hint of getting information
    key: a (possibly not) unique and sensible key to store information
    next: next state, defaults to None
    """

    def __init__(self, hint: str, key: str, next: "StepState" = None) -> None:
        self.name = None  # it will be defiled in StatesGroup
        self.group: StatesGroup = None  # it will be defiled in StatesGroup
        self.hint = hint
        self.key = key
        self.next = next


class StepStatesGroup(StatesGroup):
    """
    Describe a collection of states
    Usage: inherit this class, and add your states in the subclass
    or use config_path to load states
    WARNING: state name shouldn't be "command", "timestamp"
    name = StepState("1. Please enter Your name", "name")
    surname = StepState("2. Please enter Your surname", "surname")
    age = StepState("3. Please enter Your age", "age")
    """

    _registered: List = []

    def __init_subclass__(cls, config_path=None) -> None:
        # TODO: improve variable name: all except states should start from _
        cls.command: str | None = None
        if config_path:  # load command and Sates from yaml file
            configs = load_yaml(config_path)
            cls.command = configs.get("command", None)
            for name, description in configs.get("items", {}).items():
                setattr(cls, name, StepState(description, name))

        super().__init_subclass__()  # initialize super class

        cls.states: List[StepState] = cls._state_list
        assert len(cls.states), f"no states defined in {cls.__name__}"
        cls.entry_state: StepState = cls.states[0]  # begin state
        cls.last_state: StepState = cls.states[-1]  # end state
        for i, j in zip(cls.states, cls.states[1:]):
            i.next = j  # link states together

    @classmethod
    def register(cls, bot: telebot.TeleBot, command: str = None):
        """setup states group, register message handlers to bot
        bot: the telebot instance to register handlers
        command: the command to enter this states group, default to None,
        which will try to get `cls.command` from definition.
        """

        def start(message):
            entry_state = cls.entry_state
            bot.set_state(message.from_user.id, entry_state, message.chat.id)
            bot.send_message(message.chat.id, entry_state.hint)

        if command is None and cls.command is None:
            raise ValueError("no valid command is given")
        command = command if command else cls.command

        bot.register_message_handler(start, commands=[command])
        for s in cls._state_list:
            bot.register_message_handler(
                partial(get_text, current_state=s, bot=bot, callback=cls.final),
                state=s,
            )
        bot.add_custom_filter(StateFilter(bot))

        # register to StepStatesGroup
        cls.command = command
        cls._registered.append(cls)
        return cls

    @classmethod
    def get_state(cls, state_name: str) -> StepState:
        for state in cls.states:
            if state.name == state_name:
                return state

    @classmethod
    def get_data(cls, raw_data: dict) -> dict:
        "extract data belong to this states group"
        return {state.key: raw_data.get(state.name, "") for state in cls.states}

    @classmethod
    def final(cls, data: dict) -> str:
        """the final process to process full data when reaches the last state
        data: the full data (should be given in outter procedures)
        return: human readable information of process result
        """
        raise NotImplemented(f"Please inherit {cls.__name__} and implement final")


# TODO: add confirmation (maybe it's a final state)
def get_text(
    message, current_state: StepState, bot: telebot.TeleBot, callback: Callable
):
    """
    linearly collect text from message, store it to current state,
    and move on to the next state
    current_state: the state when message is given
    bot: the bot instance
    callback: when there is no more next state, use it to finish.
    """
    text: str = message.text
    next_state: StepState = current_state.next
    # save & retrieve data
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data[current_state.name] = text  # use name to store data
        if next_state is None:
            result = current_state.group.get_data(data)
    # next step
    if next_state is None:
        callback(result)  # let callback process it
        bot.delete_state(message.from_user.id, message.chat.id)
        bot.send_message(message.chat.id, "finished, bye 👋")
    else:
        bot.send_message(message.chat.id, next_state.hint)
        bot.set_state(message.from_user.id, next_state, message.chat.id)


class ComStates(StatesGroup):
    save = StepState("Finish & Save", "data")
