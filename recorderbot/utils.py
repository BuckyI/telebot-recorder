import os

import arrow


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
    """Get readdable time string of given timestamp

    Args:
        timestamp (int, optional): timestamp. Defaults to None (now).

    Returns:
        str: formated time string, in timezone Asia/Shanghai
    """
    t = arrow.get(timestamp) if timestamp else arrow.get()
    return t.to("Asia/Shanghai").format("YYYY-MM-DD HH:mm:ss")
