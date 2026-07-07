"""Data models for normalized NerdAxe miner data."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class MinerSample:
    """Normalized sample returned by the miner API."""

    ts: str
    hash_rate: Optional[float] = None
    hash_rate_1m: Optional[float] = None
    hash_rate_10m: Optional[float] = None
    hash_rate_1h: Optional[float] = None
    hash_rate_1d: Optional[float] = None
    temp: Optional[float] = None
    vr_temp: Optional[float] = None
    power: Optional[float] = None
    voltage: Optional[float] = None
    current: Optional[float] = None
    fan_percent: Optional[float] = None
    manual_fan_speed: Optional[float] = None
    auto_fan_speed: Optional[bool] = None
    fan_rpm: Optional[float] = None
    pid_target_temp: Optional[float] = None
    overheat_temp: Optional[float] = None
    shares_accepted: Optional[float] = None
    shares_rejected: Optional[float] = None
    best_diff: Optional[float] = None
    best_session_diff: Optional[float] = None
    wifi_rssi: Optional[float] = None
    frequency: Optional[float] = None
    actual_frequency: Optional[float] = None
    default_frequency: Optional[float] = None
    core_voltage: Optional[float] = None
    core_voltage_actual: Optional[float] = None
    default_core_voltage: Optional[float] = None
    uptime_seconds: Optional[float] = None
    last_boot: Optional[datetime] = None
    firmware_version: Optional[str] = None
    hostname: Optional[str] = None
    stratum_connected: Optional[bool] = None
    stable_device_id: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)
    raw_payload: Optional[Dict[str, Any]] = None

    def as_history_dict(self, include_raw_payload: bool = False) -> Dict[str, Any]:
        """Return the compact NDJSON representation for this sample."""

        payload = {
            "ts": self.ts,
            "hashRate": self.hash_rate,
            "hashRate1m": self.hash_rate_1m,
            "hashRate10m": self.hash_rate_10m,
            "hashRate1h": self.hash_rate_1h,
            "hashRate1d": self.hash_rate_1d,
            "temp": self.temp,
            "vrTemp": self.vr_temp,
            "power": self.power,
            "voltage": self.voltage,
            "current": self.current,
            "fanPercent": self.fan_percent,
            "manualFanSpeed": self.manual_fan_speed,
            "autoFanSpeed": self.auto_fan_speed,
            "fanRpm": self.fan_rpm,
            "pidTargetTemp": self.pid_target_temp,
            "overheatTemp": self.overheat_temp,
            "sharesAccepted": self.shares_accepted,
            "sharesRejected": self.shares_rejected,
            "bestDiff": self.best_diff,
            "bestSessionDiff": self.best_session_diff,
            "wifiRSSI": self.wifi_rssi,
            "frequency": self.frequency,
            "actualFrequency": self.actual_frequency,
            "defaultFrequency": self.default_frequency,
            "coreVoltage": self.core_voltage,
            "coreVoltageActual": self.core_voltage_actual,
            "defaultCoreVoltage": self.default_core_voltage,
            "uptimeSeconds": self.uptime_seconds,
            "lastBoot": (
                self.last_boot.isoformat().replace("+00:00", "Z")
                if self.last_boot is not None
                else None
            ),
            "version": self.firmware_version,
            "hostname": self.hostname,
            "stratumConnected": self.stratum_connected,
        }

        if self.extra:
            payload["extra"] = self.extra
        if include_raw_payload and self.raw_payload is not None:
            payload["rawPayload"] = self.raw_payload

        return payload
