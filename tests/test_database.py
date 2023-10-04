import os
from tempfile import NamedTemporaryFile

import recorderbot.storage as storage
from recorderbot.storage import DataBase


def test_database_restore_merge():
    # 测试本地备份与恢复
    with NamedTemporaryFile(mode="w+", encoding="utf-8") as f:
        db = DataBase(f.name)
        db.database.insert({"hello": "world"})
        db.restore(f.name)


def test_dataset_restore_webdav():
    # 测试WebDAV恢复
    db = DataBase("temp_empty.json")
    db.restore()
    os.remove("temp_empty.json")


def test_databse_backup():
    # 测试WebDAV备份，注意删除云端测试备份文件
    assert storage.HOSTNAME and storage.USERNAME and storage.PASSWORD
    with NamedTemporaryFile(mode="w+", encoding="utf-8") as f:
        db = DataBase(f.name)
        db.database.insert({"hello": "world"})
        db.backup()


def test_database_insert():
    # 测试插入数据
    with NamedTemporaryFile(mode="w+", encoding="utf-8") as f:
        db = DataBase(f.name)
        db.insert({"hello": "world"}, "test")
        assert db.size_of("test") == 1
