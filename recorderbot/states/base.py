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
    Usage: inherit this class, and use config_path to load states
    WARNING: state name shouldn't be "command", "timestamp"
    name = StepState("1. Please enter Your name", "name")
    surname = StepState("2. Please enter Your surname", "surname")
    age = StepState("3. Please enter Your age", "age")
    """

    _registered: List = []

    def __init_subclass__(cls, config_path) -> None:
        # TODO: improve variable name: all except states should start from _
        # load command and Sates from yaml file
        configs = load_yaml(config_path)
        cls.command_: str = configs["command"]
        cls.name_: str = configs["name"]
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
    def get_state(cls, state_name: str) -> StepState:
        for state in cls.states:
            if state.name == state_name:
                return state

    @classmethod
    def get_data(cls, raw_data: dict) -> dict:
        "extract data belong to this states group"
        return {state.key: raw_data.get(state.name, "") for state in cls.states}


class ComStates(StatesGroup):
    save = StepState("Finish & Save", "data")
