import os
import time


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


def readable_time(timestamp: int = None) -> str:
    if timestamp is None:
        timestamp = time.time()
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
