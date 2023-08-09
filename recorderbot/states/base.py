from typing import Callable

import telebot
from telebot.handler_backends import State, StatesGroup


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
