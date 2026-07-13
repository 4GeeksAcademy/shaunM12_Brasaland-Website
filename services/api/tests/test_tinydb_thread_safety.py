"""TinyDB thread-safety regression tests."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from tinydb import TinyDB
from tinydb.storages import JSONStorage

from database import LockedTable, ThreadSafeJSONStorage, _lock_for


def test_locked_table_survives_concurrent_reads_and_writes(tmp_path: Path):
    path = tmp_path / "users.json"
    db = TinyDB(path, storage=ThreadSafeJSONStorage)
    table = LockedTable(db.table("users"), _lock_for(path))
    table.insert({"email": "seed@brasaland.com", "id": 1})

    errors: list[BaseException] = []

    def writer(i: int) -> None:
        try:
            table.insert({"email": f"user{i}@brasaland.com", "id": i + 10})
        except BaseException as exc:  # noqa: BLE001 - collect any race failure
            errors.append(exc)

    def reader() -> None:
        try:
            rows = table.all()
            assert rows is not None
            assert len(rows) >= 1
        except BaseException as exc:  # noqa: BLE001 - collect any race failure
            errors.append(exc)

    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = []
        for i in range(40):
            futures.append(pool.submit(writer, i))
            futures.append(pool.submit(reader))
            futures.append(pool.submit(reader))
        for future in as_completed(futures):
            future.result()

    assert errors == []
    assert len(table.all()) == 41
    db.close()


def test_thread_safe_storage_retries_json_decode_error(tmp_path: Path, monkeypatch):
    path = tmp_path / "auth.json"
    storage = ThreadSafeJSONStorage(str(path))
    storage.write({"users": {}})

    calls = {"n": 0}
    original = JSONStorage.read

    def flaky_read(self):  # type: ignore[no-untyped-def]
        calls["n"] += 1
        if calls["n"] == 1:
            raise json.JSONDecodeError("Expecting value", "", 0)
        return original(self)

    monkeypatch.setattr(JSONStorage, "read", flaky_read)

    assert storage.read() == {"users": {}}
    assert calls["n"] == 2
    storage.close()
