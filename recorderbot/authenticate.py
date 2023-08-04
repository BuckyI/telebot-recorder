from tinydb import Query, TinyDB


class Authenticator:
    tablename = "register_info"

    def __init__(self, db_path: str = "db.json") -> None:
        self.db_path = db_path
        self.db = TinyDB(db_path)
        self.db.default_table_name = self.tablename  # set default table

    def register(self, chat_id: int) -> int:
        """
        Add a record. Please avoid timestamp collision.
        Records with same timestamp will be overwritten.
        """
        doc_id = self.db.insert({"chat_id": chat_id})
        return doc_id

    def is_registered(self, chat_id: int) -> bool:
        return self.db.contains(Query().chat_id == chat_id)
