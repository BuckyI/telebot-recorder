from functools import partial
from pathlib import Path
from typing import Callable, Iterator, List

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

    def __init__(self, hint: str, key: str) -> None:
        self.hint: str = hint
        self.key: str = key
        # inter state property
        self.next: "StepState" = None
        # group related property
        self.group: "StepStatesGroup" = None
        self.name: str = None


class StepStatesGroup:
    """
    Class representing common states.
    [refer to: telebot.handler_backends.StatesGroup ]
    use config_path to load states
    WARNING: state name shouldn't conflict with reserved property
    name = StepState("1. Please enter Your name", "name")
    surname = StepState("2. Please enter Your surname", "surname")
    age = StepState("3. Please enter Your age", "age")
    """

    def __init__(self, configs: str | dict) -> None:
        if isinstance(configs, str):
            configs = load_yaml(configs)  # load from file path
        elif isinstance(configs, dict):
            configs = configs  # load from dict
        assert self.validate_config(configs), "configuration incomplete!"
        self._cfg = configs
        self._state_list: List[StepState] = []

        step_idx, step_total = 1, len(configs["items"])
        for name, description in configs["items"].items():
            # add suffix of description
            description = f"{description} ({step_idx}/{step_total})"
            step_idx += 1

            state = StepState(description, name)
            state.group = self
            state.name = f"{self.name}:{name}"
            setattr(self, name, state)
            self._state_list.append(state)

        for i, j in zip(self._state_list, self._state_list[1:]):
            i.next = j  # link states together

    def __str__(self) -> str:
        return f"StepStatesGroup {self.name}"

    @property
    def name(self) -> str:
        "state group name"
        return self._cfg["name"]

    @property
    def command(self) -> str:
        "command to enter this states group"
        return self._cfg["command"]

    @property
    def description(self) -> str:
        "description of this states group"
        return self._cfg["description"]

    @property
    def state_list(self) -> List[StepState]:
        "states of this group"
        return self._state_list

    @property
    def entry_state(self) -> StepState:
        return self._state_list[0]  # begin state

    @property
    def last_state(self) -> StepState:
        return self._state_list[-1]  # end state

    def get_state(self, state_name: str) -> StepState:
        for state in self.state_list:
            if state.name == state_name:
                return state

    def get_data(self, raw_data: dict) -> dict:
        "extract data belong to this states group"
        return {state.key: raw_data.get(state.name, "") for state in self.state_list}

    @classmethod
    def validate_config(cls, cfg: dict) -> bool:
        return all(key in cfg for key in ["command", "name", "description", "items"])

    @classmethod
    def validated_configs(cls, path: str) -> Iterator[dict]:
        "search for valid yaml file to load StatesGroup"
        for f in Path(path).glob("*.yaml"):
            cfg = load_yaml(str(f))
            if not cfg.get("enable", False):
                continue  # 对文件夹扫描时，额外通过 enable 选项过滤
            if cls.validate_config(cfg):
                yield cfg


class ComStates(StatesGroup):
    save = StepState("Finish & Save", "data")
