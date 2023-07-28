import logging
import re
import time
from collections import namedtuple
from typing import Any, List

from tinydb import Query, TinyDB

from .utils import readable_time


class RecordItem(dict):
    required = ("timestamp", "content", "type")

    def __init__(
        self,
        timestamp: int,
        content: str,
        type: str = "normal",
        /,
        tags: List[str] = [],
        **kwargs,
    ):
        "necessary keys with optional additional keys"
        super().__init__(timestamp=timestamp, content=content, type=type)
        kwargs = {k: v for k, v in kwargs.items() if v}  # filter empty values
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
    def __init__(self, db_path: str = "db.json") -> None:
        self.db = TinyDB(db_path)

    def record(self, item: RecordItem) -> int:
        return self.db.insert(item)

    def search(self, substr: str) -> RecordItem:
        for i in self.db.search(Query().content.search(substr, flags=re.IGNORECASE)):
            yield RecordItem.from_dict(i)
