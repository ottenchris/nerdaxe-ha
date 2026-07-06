"""Normalize AxeOS/ESP-Miner API payloads into stable integration data."""

from __future__ import annotations

from datetime import datetime, timezone
import math
import re
from typing import Any, Dict, Iterable, Optional

from .models import MinerSample

_DIFFICULTY_SUFFIXES = {
    "k": 1_000,
    "m": 1_000_000,
    "g": 1_000_000_000,
    "t": 1_000_000_000_000,
    "p": 1_000_000_000_000_000,
}

_NORMALIZED_TOP_LEVEL_KEYS = {
    "hashRate",
    "hashRate_1m",
    "hashRate_10m",
    "hashRate_1h",
    "hashRate_1d",
    "temp",
    "vrTemp",
    "power",
    "voltage",
    "asicVoltage",
    "asicVoltageMv",
    "current",
    "currentA",
    "fanspeed",
    "fanPercent",
    "fanrpm",
    "fanRpm",
    "sharesAccepted",
    "sharesRejected",
    "bestDiff",
    "bestSessionDiff",
    "wifiRSSI",
    "frequency",
    "coreVoltage",
    "coreVoltageMv",
    "coreVoltageActual",
    "coreVoltageActualMv",
    "hostname",
    "version",
    "uptimeSeconds",
    "stratum",
    "connected",
    "mac",
    "macAddr",
    "wifiMac",
    "ethMac",
    "chipId",
    "chipID",
    "serial",
    "serialNumber",
    "deviceId",
}

_STABLE_ID_PATHS = (
    "macAddr",
    "mac",
    "wifiMac",
    "ethMac",
    "deviceId",
    "serialNumber",
    "serial",
    "chipId",
    "chipID",
    "system.mac",
    "network.mac",
)

_CONNECTED_PATHS = (
    "connected",
    "stratum.connected",
    "stratum.isConnected",
    "stratum.pool.connected",
    "stratum.pools.0.connected",
    "stratum.pools.0.isConnected",
    "stratum.pools.0.alive",
    "pool.connected",
)


def utc_now_iso() -> str:
    """Return the current UTC time as an ISO timestamp."""

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def slugify_identifier(value: str) -> str:
    """Create a filesystem and unique-id friendly identifier."""

    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(value).strip().lower())
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug or "unknown"


def pick_path(payload: Any, path: str) -> Any:
    """Pick a dotted path from dict/list data."""

    current = payload
    for part in path.split("."):
        if isinstance(current, dict):
            if part not in current:
                return None
            current = current[part]
            continue
        if isinstance(current, list):
            try:
                index = int(part)
            except ValueError:
                return None
            if index < 0 or index >= len(current):
                return None
            current = current[index]
            continue
        return None
    return current


def pick_first(payload: Any, paths: Iterable[str]) -> Any:
    """Return the first present value for a set of dotted paths."""

    for path in paths:
        value = pick_path(payload, path)
        if value is not None:
            return value
    return None


def to_float(value: Any) -> Optional[float]:
    """Convert API values to finite floats."""

    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value) if math.isfinite(float(value)) else None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            parsed = float(text)
        except ValueError:
            return None
        return parsed if math.isfinite(parsed) else None
    return None


def to_difficulty(value: Any) -> Optional[float]:
    """Convert plain or suffixed difficulty values to floats."""

    plain = to_float(value)
    if plain is not None:
        return plain
    if not isinstance(value, str):
        return None

    match = re.fullmatch(r"\s*([+-]?\d+(?:\.\d+)?)\s*([kKmMgGtTpP])\s*", value)
    if not match:
        return None
    parsed = float(match.group(1)) * _DIFFICULTY_SUFFIXES[match.group(2).lower()]
    return parsed if math.isfinite(parsed) else None


def to_bool(value: Any) -> Optional[bool]:
    """Convert common API truthy/falsy values to bool."""

    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"true", "yes", "on", "online", "connected", "1"}:
            return True
        if text in {"false", "no", "off", "offline", "disconnected", "0"}:
            return False
    return None


def to_text(value: Any) -> Optional[str]:
    """Convert simple API values to non-empty strings."""

    if value is None:
        return None
    text = str(value).strip()
    return text or None


def normalize_voltage_to_volts(value: Any) -> Optional[float]:
    """Normalize board/input voltage to volts.

    AxeOS/ESP-Miner payloads are inconsistent across builds. Values above 100
    are treated as millivolts; small values are treated as volts.
    """

    parsed = to_float(value)
    if parsed is None:
        return None
    if abs(parsed) > 100:
        return parsed / 1000
    return parsed


def sanitize_history_value(value: Any, depth: int = 0) -> Any:
    """Return a JSON-safe copy of an arbitrary API value."""

    if depth > 8:
        return None
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, (int, float)):
        return value if math.isfinite(float(value)) else None
    if isinstance(value, list):
        return [sanitize_history_value(item, depth + 1) for item in value]
    if isinstance(value, dict):
        return {
            str(key): sanitize_history_value(value[key], depth + 1)
            for key in sorted(value.keys(), key=str)
        }
    return str(value)


def extract_extra(payload: Any) -> Dict[str, Any]:
    """Extract sanitized fields not promoted to normalized sample fields."""

    if not isinstance(payload, dict):
        return {}

    extra: Dict[str, Any] = {}
    for key in sorted(payload.keys(), key=str):
        if key in _NORMALIZED_TOP_LEVEL_KEYS:
            continue
        extra[str(key)] = sanitize_history_value(payload[key])
    return extra


def find_stable_device_id(payload: Any) -> Optional[str]:
    """Find a stable device ID from API data if one exists."""

    for path in _STABLE_ID_PATHS:
        value = to_text(pick_path(payload, path))
        if value:
            return slugify_identifier(value)
    return None


def infer_stratum_connected(payload: Any) -> Optional[bool]:
    """Infer pool/stratum connectivity from known API shapes."""

    for path in _CONNECTED_PATHS:
        parsed = to_bool(pick_path(payload, path))
        if parsed is not None:
            return parsed

    pools = pick_path(payload, "stratum.pools")
    if isinstance(pools, list) and pools:
        parsed_pools = [
            to_bool(pool.get("connected"))
            for pool in pools
            if isinstance(pool, dict) and "connected" in pool
        ]
        parsed_pools = [item for item in parsed_pools if item is not None]
        if parsed_pools:
            return any(parsed_pools)

    return None


def normalize_miner_payload(payload: Any, now: Optional[datetime] = None) -> MinerSample:
    """Normalize a raw AxeOS/ESP-Miner info payload."""

    if not isinstance(payload, dict):
        payload = {}

    ts = (
        now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        if now is not None
        else utc_now_iso()
    )

    return MinerSample(
        ts=ts,
        hash_rate=to_float(pick_first(payload, ("hashRate",))),
        hash_rate_1m=to_float(pick_first(payload, ("hashRate_1m",))),
        hash_rate_10m=to_float(pick_first(payload, ("hashRate_10m",))),
        hash_rate_1h=to_float(pick_first(payload, ("hashRate_1h",))),
        hash_rate_1d=to_float(pick_first(payload, ("hashRate_1d",))),
        temp=to_float(pick_first(payload, ("temp",))),
        vr_temp=to_float(pick_first(payload, ("vrTemp",))),
        power=to_float(pick_first(payload, ("power",))),
        voltage=normalize_voltage_to_volts(
            pick_first(payload, ("voltage", "asicVoltage", "asicVoltageMv"))
        ),
        current=to_float(pick_first(payload, ("currentA", "current"))),
        fan_percent=to_float(pick_first(payload, ("fanspeed", "fanPercent"))),
        fan_rpm=to_float(pick_first(payload, ("fanrpm", "fanRpm"))),
        shares_accepted=to_float(
            pick_first(payload, ("sharesAccepted", "stratum.pools.0.accepted"))
        ),
        shares_rejected=to_float(
            pick_first(payload, ("sharesRejected", "stratum.pools.0.rejected"))
        ),
        best_diff=to_difficulty(
            pick_first(payload, ("bestDiff", "stratum.pools.0.bestDiff"))
        ),
        best_session_diff=to_difficulty(pick_first(payload, ("bestSessionDiff",))),
        wifi_rssi=to_float(pick_first(payload, ("wifiRSSI",))),
        frequency=to_float(pick_first(payload, ("frequency",))),
        core_voltage=to_float(pick_first(payload, ("coreVoltage", "coreVoltageMv"))),
        core_voltage_actual=to_float(
            pick_first(payload, ("coreVoltageActual", "coreVoltageActualMv"))
        ),
        uptime_seconds=to_float(pick_first(payload, ("uptimeSeconds",))),
        firmware_version=to_text(pick_first(payload, ("version",))),
        hostname=to_text(pick_first(payload, ("hostname",))),
        stratum_connected=infer_stratum_connected(payload),
        stable_device_id=find_stable_device_id(payload),
        extra=extract_extra(payload),
        raw_payload=sanitize_history_value(payload),
    )
