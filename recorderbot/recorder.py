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
    def __init__(self, db_path: str = "db.json") -> None:
        self.db_path = db_path
        self.db = TinyDB(db_path)

        try:
            # use environment variables to initialize a WebDAV client
            self.storage = WebDAV()
        except Exception:
            logging.warning("WebDAV initialization failed, can't backup.")
            self.storage = None

    @property
    def size(self):
        return len(self.db)

    def record(self, item: RecordItem) -> int:
        doc_id = self.db.insert(item)
        self.backup()
        return doc_id

    def search(self, substr: str) -> RecordItem:
        for i in self.db.search(Query().content.search(substr, flags=re.IGNORECASE)):
            yield RecordItem.from_dict(i)

    def merge(self, path: str) -> int:
        """Merge records from another json file. Use timestamp to identify same records.

        Args:
            path (str): json file path

        Returns:
            int: the newly added record count
        """
        db = TinyDB(path)
        count = 0
        for item in db:
            if self.db.contains(Query().timestamp == item["timestamp"]):
                continue
            item = dict(item)  # remove doc_id
            self.db.insert(item)
            count += 1
            logging.info("add record:", item)
        self.backup()
        return count

    def merge_from_backup(self) -> int:
        "return updated record count"
        if not self.storage:
            logging.error("you don't have a valid storage")
            return
        try:
            self.storage.download_latest("temp.json")
            count = self.merge("temp.json")
            return count
            # TODO: remove temp file
        except Exception:
            logging.error("the downloaded file may not be a valid backup")
            return -1

    def backup(self):
        """if WebDAV is available, backup the database"""
        if not self.storage:
            logging.error("you don't have a valid storage")
            return
        filename = "%s.json" % readable_time(format="YYYYMMDDHHmmss")
        self.storage.upload(self.db_path, filename)
        return filename
