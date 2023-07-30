import logging
from pathlib import Path
from typing import Final

from decouple import config
from webdav3.client import Client

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
        logging.info("latest file is %s" % latest)
        self.client.download(latest, dest)
