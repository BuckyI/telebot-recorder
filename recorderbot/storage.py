import logging
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Final, List, Optional

from decouple import config
from tinydb import Query, TinyDB
from webdav3.client import Client

from .utils import readable_time

HOSTNAME: Final = config("WEBDAV_HOSTNAME", default="")
USERNAME: Final = config("WEBDAV_USERNAME", default="")
PASSWORD: Final = config("WEBDAV_PASSWORD", default="")


class WebDAV:
    """
    Simple client to upload and retrieve files
    Note: avoid subfolder related operations
    """

    def __init__(
        self,
        hostname: str = HOSTNAME,
        username: str = USERNAME,
        password: str = PASSWORD,
    ) -> None:
        """initiate a WebDAV client, it will try to get parameters from env if not given"""
        assert all((hostname, username, password)), "Please set WEBDAV parameters"

        options = {
            "webdav_hostname": hostname,
            "webdav_login": username,
            "webdav_password": password,
            "disable_check": True,  # 坚果云似乎不支持 check，会无法访问资源
            "verbose": True,
        }
        self.client = Client(options)
        try:
            self.client.list()  # test function
        except Exception:
            logging.error("WebDAV failed to launch, check your settings!")

    @property
    def resources(self):
        return self.client.list(get_info=True)

    def exists(self, name: str) -> bool:
        name = Path(name).name  # extract base filename
        return any(r["name"] == name for r in self.resources)

    def upload(self, source: str, dest: str) -> None:
        assert Path(source).exists(), "file to be uploaded does not exist"
        if self.exists(dest):
            logging.warning("%s already exists, it will be overwrite" % dest)

        self.client.upload(dest, source)

    def download_latest(self, dest: str, filter: str = ".json") -> None:
        latest = max([i for i in self.client.list() if i.endswith(filter)])
        logging.info("download latest file %s from webdav" % latest)
        self.client.download(latest, dest)

    def delete(self):
        raise NotImplementedError


class DataBase:
    """TinyDB management with WebDAV"""

    def __init__(self, path: str = "db.json", websync=True) -> None:
        self.db_path = path
        self.database = TinyDB(path)
        self.webdav = WebDAV() if websync else None

    def insert(self, item: dict, table: str = None) -> int:
        """
        Add a record. Please avoid timestamp collision.
        Records with same timestamp will be overwritten.
        """
        table = self.database.table(table) if table else self.database
        doc_id = table.insert(item) if item else 0  # if item is empty, skip it
        logging.info("new record of id {}: {}".format(doc_id, item))
        return doc_id

    def size_of(self, table: str = None) -> int:
        table = self.database.table(table) if table else self.database
        return len(table)

    def backup(self) -> str:
        """if WebDAV is available, backup the database"""
        if self.webdav is None:
            logging.error("WebDAV is not available")
            return
        filename = "%s.json" % readable_time(format="YYYYMMDDHHmmss")
        self.webdav.upload(self.db_path, filename)
        logging.error("backup %s to WebDAV", filename)
        return filename

    def restore(self, path: str = None) -> int:
        """restore data from file
        path (str, optional): file with data to restore. Defaults to None.
        return: updated item number
        """
        if path is None:
            if self.webdav is None:
                logging.error("WebDAV is not available")
                return
            path = "temp.json"
            self.webdav.download_latest(path)

        source_db = TinyDB(path)
        dest_db = self.database

        source_tables = (source_db.table(tb) for tb in source_db.tables())
        dest_tables = (dest_db.table(tb) for tb in source_db.tables())
        count = 0
        for src, dst in zip(source_tables, dest_tables):
            for doc in src:
                if not dst.contains(Query().fragment(doc)):
                    dst.insert(dict(doc))  # removing doc id
                    count += 1
        logging.info("restore %d records from file %s", count, path)
        return count
