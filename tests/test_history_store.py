from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from custom_components.nerdaxe_miner.history_store import NerdAxeHistoryStore
from custom_components.nerdaxe_miner.models import MinerSample


def fixed_now() -> datetime:
    return datetime(2026, 3, 11, 12, 0, 0, tzinfo=timezone.utc)


class HistoryStoreTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    async def asyncTearDown(self) -> None:
        self._tmp.cleanup()

    async def test_appends_samples_to_utc_day_file(self) -> None:
        store = NerdAxeHistoryStore(
            self.root,
            max_bytes=1024 * 1024,
            raw_keep_days=30,
            now_provider=fixed_now,
        )
        sample = MinerSample(
            ts="2026-03-10T23:59:59Z",
            hash_rate=123.4,
            temp=58.0,
            hostname="miner-one",
        )

        await store.async_append_sample(sample)

        history_file = self.root / "history-2026-03-10.ndjson"
        self.assertTrue(history_file.exists())
        entry = json.loads(history_file.read_text(encoding="utf-8").strip())
        self.assertEqual(entry["ts"], "2026-03-10T23:59:59Z")
        self.assertEqual(entry["hashRate"], 123.4)
        self.assertEqual(entry["hostname"], "miner-one")
        self.assertNotIn("rawPayload", entry)

    async def test_optionally_stores_raw_payload(self) -> None:
        store = NerdAxeHistoryStore(
            self.root,
            max_bytes=1024 * 1024,
            raw_keep_days=30,
            store_raw_payload=True,
            now_provider=fixed_now,
        )
        sample = MinerSample(
            ts="2026-03-10T10:00:00Z",
            hash_rate=1.0,
            raw_payload={"hashRate": 1, "nested": {"ok": True}},
        )

        await store.async_append_sample(sample)

        entry = json.loads(
            (self.root / "history-2026-03-10.ndjson")
            .read_text(encoding="utf-8")
            .strip()
        )
        self.assertEqual(entry["rawPayload"], {"hashRate": 1, "nested": {"ok": True}})

    async def test_appends_fetch_error_events(self) -> None:
        store = NerdAxeHistoryStore(
            self.root,
            max_bytes=1024 * 1024,
            raw_keep_days=30,
            now_provider=fixed_now,
        )

        await store.async_append_fetch_error(
            "coordinator",
            RuntimeError("miner offline"),
            ts="2026-03-10T10:00:00Z",
        )

        entry = json.loads(
            (self.root / "history-2026-03-10.ndjson")
            .read_text(encoding="utf-8")
            .strip()
        )
        self.assertEqual(entry["eventType"], "fetch_error")
        self.assertEqual(entry["source"], "coordinator")
        self.assertEqual(entry["message"], "miner offline")

    async def test_gzips_raw_files_older_than_keep_window(self) -> None:
        store = NerdAxeHistoryStore(
            self.root,
            max_bytes=1024 * 1024,
            raw_keep_days=1,
            now_provider=fixed_now,
        )
        await store.async_append_sample(
            MinerSample(ts="2026-03-10T10:00:00Z", hash_rate=321)
        )

        await store.async_maintain()

        self.assertFalse((self.root / "history-2026-03-10.ndjson").exists())
        archive = self.root / "history-2026-03-10.ndjson.gz"
        self.assertTrue(archive.exists())
        with gzip.open(archive, "rt", encoding="utf-8") as file:
            entry = json.loads(file.read().strip())
        self.assertEqual(entry["hashRate"], 321)

    async def test_budget_deletes_oldest_compressed_archives_first(self) -> None:
        oldest = self.root / "history-2026-03-01.ndjson.gz"
        newest = self.root / "history-2026-03-02.ndjson.gz"
        current = self.root / "history-2026-03-11.ndjson"
        oldest.write_bytes(b"x" * 700)
        newest.write_bytes(b"y" * 200)
        current.write_bytes(b"z" * 200)

        store = NerdAxeHistoryStore(
            self.root,
            max_bytes=1024,
            raw_keep_days=30,
            now_provider=fixed_now,
        )

        await store.async_maintain()

        self.assertFalse(oldest.exists())
        self.assertTrue(newest.exists())
        self.assertTrue(current.exists())


if __name__ == "__main__":
    unittest.main()
