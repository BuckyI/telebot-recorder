import telebot
from tinydb import Query, TinyDB

from .storage import DataBase


class Authenticator:
    tablename = "register_info"

    def __init__(self, bot: telebot.TeleBot, db: DataBase) -> None:
        self.bot = bot
        self.db = db
        self.table = db.database.table(self.tablename)  # use table

    def register_command(self, command: str = "register"):
        self.bot.register_message_handler(self.register, commands=[command])

    def register(self, message: telebot.types.Message):
        bot: telebot.TeleBot = self.bot
        if self.is_registered(message.chat.id):
            bot.send_message(message.chat.id, "You have already registered 🤖")
        else:
            doc_id = self.db.insert({"chat_id": message.chat.id}, self.tablename)
            bot.send_message(message.chat.id, f"Registered successfully 🎉 ({doc_id})")
            self.db.backup()

    def is_registered(self, chat_id: int) -> bool:
        return self.table.contains(Query().chat_id == chat_id)
