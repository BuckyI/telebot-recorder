import logging
import re
from typing import Any, List

from tinydb import Query, TinyDB

from .storage import WebDAV
from .utils import readable_time


class RecordItem(dict):
    required = ("timestamp", "content", "type")
    optional = ("tags",)  # supported additional keys in kwargs

    def __init__(
        self,
        timestamp: int,
        content: str,
        type: str = "normal",
        /,
        **kwargs,
    ):
        "necessary keys with optional additional keys"
        super().__init__(timestamp=timestamp, content=content, type=type)
        # filter optional non-empty key-values
        kwargs = {k: v for k, v in kwargs.items() if v and v in self.optional}
        self.update(kwargs)

    def to_str(self) -> str:
        return "{} record at {}:\n{}".format(
            self["type"],
            readable_time(self["timestamp"]),
            self["content"],
        )

    @classmethod
    def from_dict(cls, d: dict):
        """create a RecordItem instance from a dict"""
        if all((k in d for k in cls.required)):
            others = {k: v for k, v in d.items() if k not in cls.required}
            return cls(d["timestamp"], d["content"], d["type"], **others)
        else:
            logging.error(f"necessary key missing when creating {cls}")
            return cls(0, "", "error")


class Recorder:
    tablename = "records"

    def __init__(self, db_path: str = "db.json") -> None:
        self.db_path = db_path
        self.db = TinyDB(db_path)
        self.db.default_table_name = self.tablename  # set table name of records

    @property
    def size(self):
        return len(self.db)

    def record(self, item: RecordItem) -> int:
        """
        Add a record. Please avoid timestamp collision.
        Records with same timestamp will be overwritten.
        """
        doc_id = self.db.insert(item)
        logging.info("new record of id {}: {}".format(doc_id, item))
        return doc_id

    def search(self, substr: str) -> RecordItem:
        for i in self.db.search(Query().content.search(substr, flags=re.IGNORECASE)):
            yield RecordItem.from_dict(i)

    def exits(self, record: dict) -> bool:
        "check if given record item exists by timestamp"
        return self.db.contains(Query().timestamp == record["timestamp"])

    def merge(self, path: str) -> int:
        """Merge records from another json file. Use timestamp to identify same records.

        Args:
            path (str): json file path

        Returns:
            int: the newly added record count
        """
        db = TinyDB(path).table(self.tablename)
        for item in db:
            if not self.exits(item):
                self.record(dict(item))  # remove doc_id
                count += 1
                logging.info("add record:", item)
        if count == 0:
            logging.warning("no valid data is in the source")
        return count
