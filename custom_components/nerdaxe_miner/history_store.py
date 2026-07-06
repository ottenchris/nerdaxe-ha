"""Local NDJSON history store for NerdAxe miner samples."""

from __future__ import annotations

import asyncio
import functools
import gzip
import json
import os
import re
import shutil
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional

from .models import MinerSample
from .normalizer import utc_now_iso

_DAY_FILE_RE = re.compile(r"^history-(\d{4}-\d{2}-\d{2})\.ndjson$")
_DAY_GZIP_FILE_RE = re.compile(r"^history-(\d{4}-\d{2}-\d{2})\.ndjson\.gz$")


@dataclass(frozen=True)
class HistoryFile:
    """A daily history file on disk."""

    day_key: str
    path: Path
    compressed: bool


def _parse_iso_datetime(value: Any) -> Optional[datetime]:
    if not isinstance(value, str):
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def day_key_from_ts(value: Any) -> Optional[str]:
    """Return YYYY-MM-DD in UTC for an ISO timestamp."""

    parsed = _parse_iso_datetime(value)
    if parsed is None:
        return None
    return parsed.strftime("%Y-%m-%d")


def _today_key(now: datetime) -> str:
    return now.astimezone(timezone.utc).strftime("%Y-%m-%d")


def _day_start(day_key: str) -> datetime:
    return datetime.strptime(day_key, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def _history_file_path(root_dir: Path, day_key: str) -> Path:
    return root_dir / f"history-{day_key}.ndjson"


def _history_gzip_path(root_dir: Path, day_key: str) -> Path:
    return root_dir / f"history-{day_key}.ndjson.gz"


def list_daily_history_files(root_dir: Path) -> list[HistoryFile]:
    """List raw and compressed daily history files."""

    if not root_dir.exists():
        return []

    by_day: dict[str, HistoryFile] = {}
    for entry in root_dir.iterdir():
        if not entry.is_file() or entry.name.endswith(".tmp"):
            continue

        raw_match = _DAY_FILE_RE.fullmatch(entry.name)
        if raw_match:
            by_day[raw_match.group(1)] = HistoryFile(
                day_key=raw_match.group(1),
                path=entry,
                compressed=False,
            )
            continue

        gzip_match = _DAY_GZIP_FILE_RE.fullmatch(entry.name)
        if gzip_match and gzip_match.group(1) not in by_day:
            by_day[gzip_match.group(1)] = HistoryFile(
                day_key=gzip_match.group(1),
                path=entry,
                compressed=True,
            )

    return sorted(by_day.values(), key=lambda item: item.day_key)


class NerdAxeHistoryStore:
    """Append-only daily NDJSON storage with gzip and byte-budget retention."""

    def __init__(
        self,
        root_dir: Path | str,
        *,
        max_bytes: int,
        raw_keep_days: int,
        store_raw_payload: bool = False,
        cleanup_every_writes: int = 100,
        executor_job: Optional[Callable[..., Any]] = None,
        now_provider: Optional[Callable[[], datetime]] = None,
    ) -> None:
        self.root_dir = Path(root_dir)
        self.max_bytes = max(1, int(max_bytes))
        self.raw_keep_days = max(1, int(raw_keep_days))
        self.store_raw_payload = bool(store_raw_payload)
        self.cleanup_every_writes = max(1, int(cleanup_every_writes))
        self._executor_job = executor_job
        self._now_provider = now_provider or (lambda: datetime.now(timezone.utc))
        self._lock = asyncio.Lock()
        self._writes_since_cleanup = 0

    async def async_append_sample(self, sample: MinerSample) -> None:
        """Append a normalized miner sample."""

        await self.async_append_entry(
            sample.as_history_dict(include_raw_payload=self.store_raw_payload)
        )

    async def async_append_fetch_error(
        self,
        source: str,
        error: Exception,
        *,
        ts: Optional[str] = None,
    ) -> None:
        """Append a fetch error event."""

        entry: dict[str, Any] = {
            "ts": ts or utc_now_iso(),
            "eventType": "fetch_error",
            "source": source,
            "message": str(error),
            "errorName": type(error).__name__,
        }

        if error.__class__.__name__ == "MinerApiError":
            entry["upstreamUrl"] = getattr(error, "url", None)
            entry["upstreamStatus"] = getattr(error, "status", None)
            entry["upstreamBodyPreview"] = getattr(error, "body_preview", None)

        await self.async_append_entry(entry)

    async def async_append_entry(self, entry: Dict[str, Any]) -> None:
        """Append a history entry and periodically run retention."""

        async with self._lock:
            await self._run_io(self._append_entry_sync, entry)
            self._writes_since_cleanup += 1
            if self._writes_since_cleanup >= self.cleanup_every_writes:
                self._writes_since_cleanup = 0
                await self._run_io(self._maintain_sync)

    async def async_maintain(self) -> None:
        """Run gzip and byte-budget maintenance now."""

        async with self._lock:
            await self._run_io(self._maintain_sync)

    async def _run_io(self, func: Callable[..., Any], *args: Any) -> Any:
        if self._executor_job is not None:
            return await self._executor_job(func, *args)
        loop = asyncio.get_running_loop()
        call = functools.partial(func, *args)
        return await loop.run_in_executor(None, call)

    def _append_entry_sync(self, entry: Dict[str, Any]) -> None:
        safe_entry = dict(entry)
        if not day_key_from_ts(safe_entry.get("ts")):
            safe_entry["ts"] = utc_now_iso()

        day_key = day_key_from_ts(safe_entry["ts"])
        if day_key is None:
            raise ValueError("failed to resolve history day")

        self.root_dir.mkdir(parents=True, exist_ok=True)
        file_path = _history_file_path(self.root_dir, day_key)
        with file_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(safe_entry, sort_keys=True, separators=(",", ":")))
            file.write("\n")

    def _maintain_sync(self) -> None:
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self._gzip_old_raw_files_sync()
        self._enforce_budget_sync()

    def _gzip_old_raw_files_sync(self) -> None:
        today_start = _day_start(_today_key(self._now_provider()))
        cutoff = today_start - timedelta(days=self.raw_keep_days - 1)

        for entry in list_daily_history_files(self.root_dir):
            if entry.compressed:
                continue
            if _day_start(entry.day_key) >= cutoff:
                continue
            self._gzip_file_sync(entry)

    def _gzip_file_sync(self, entry: HistoryFile) -> None:
        target = _history_gzip_path(self.root_dir, entry.day_key)
        tmp_target = target.with_suffix(target.suffix + ".tmp")

        if not target.exists():
            with (
                entry.path.open("rb") as source,
                gzip.open(
                    tmp_target,
                    "wb",
                    compresslevel=9,
                ) as target_file,
            ):
                shutil.copyfileobj(source, target_file)
            os.replace(tmp_target, target)

        with suppress(FileNotFoundError):
            entry.path.unlink()

    def _iter_budget_files_sync(self) -> Iterable[Path]:
        if not self.root_dir.exists():
            return []
        return [
            entry
            for entry in self.root_dir.iterdir()
            if entry.is_file() and not entry.name.endswith(".tmp")
        ]

    def _total_bytes_sync(self) -> int:
        return sum(path.stat().st_size for path in self._iter_budget_files_sync())

    def _enforce_budget_sync(self) -> None:
        total = self._total_bytes_sync()
        if total <= self.max_bytes:
            return

        today_key = _today_key(self._now_provider())
        files = list_daily_history_files(self.root_dir)

        compressed_candidates = sorted(
            (item for item in files if item.compressed),
            key=lambda item: item.day_key,
        )
        total = self._delete_until_under_budget_sync(total, compressed_candidates)
        if total <= self.max_bytes:
            return

        non_current_candidates = sorted(
            (
                item
                for item in list_daily_history_files(self.root_dir)
                if item.day_key != today_key
            ),
            key=lambda item: item.day_key,
        )
        self._delete_until_under_budget_sync(total, non_current_candidates)

    def _delete_until_under_budget_sync(
        self,
        total: int,
        candidates: Iterable[HistoryFile],
    ) -> int:
        for entry in candidates:
            if total <= self.max_bytes:
                break
            try:
                size = entry.path.stat().st_size
                entry.path.unlink()
                total -= size
            except FileNotFoundError:
                continue
        return total
