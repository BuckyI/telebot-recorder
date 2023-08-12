import os

import arrow
import requests
import yaml


def is_small_file(file_path: str) -> bool:
    """Confirm the file size is within 50MB
    According to https://core.telegram.org/bots/api#sending-files
    return: True for valid small file
    """
    if os.path.exists(file_path):
        size_bytes = os.path.getsize(file_path)
        size_mb = size_bytes / (1024 * 1024)
        return size_mb <= 50
    return False


def readable_time(timestamp: int = None, format: str = "YYYY-MM-DD HH:mm:ss") -> str:
    """Get readdable time string of given timestamp

    Args:
        timestamp (int, optional): timestamp. Defaults to None (now).
        format (str, optional): format. Defaults to "YYYY-MM-DD HH:mm:ss".

    Returns:
        str: formated time string, in timezone Asia/Shanghai
    """
    t = arrow.get(timestamp) if timestamp else arrow.get()
    return t.to("Asia/Shanghai").format(format)


def save_file(url: str, filename="temp.txt"):
    response = requests.get(url)
    with open(filename, "wb") as f:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)


def load_yaml(path: str) -> dict:
    return yaml.load(open(path), Loader=yaml.FullLoader) if os.path.exists(path) else {}
