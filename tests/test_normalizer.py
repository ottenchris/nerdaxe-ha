from __future__ import annotations

from datetime import datetime, timezone
import unittest

from custom_components.nerdaxe_miner.normalizer import (
    find_stable_device_id,
    infer_stratum_connected,
    normalize_miner_payload,
    sanitize_history_value,
    to_difficulty,
    to_float,
)


class NormalizerTest(unittest.TestCase):
    def test_normalizes_common_axeos_payload(self) -> None:
        payload = {
            "hashRate": "812.5",
            "hashRate_1m": 800,
            "hashRate_10m": "790.25",
            "hashRate_1h": "780",
            "hashRate_1d": "770",
            "temp": "58.2",
            "vrTemp": 61,
            "power": "12.5",
            "voltage": 5000,
            "current": "2.5",
            "fanspeed": 44,
            "fanrpm": "6200",
            "sharesAccepted": "12",
            "sharesRejected": "1",
            "bestDiff": "1.5G",
            "bestSessionDiff": "250M",
            "wifiRSSI": "-63",
            "frequency": "550",
            "coreVoltage": "1090",
            "coreVoltageActual": 1084,
            "uptimeSeconds": "12345",
            "hostname": "nerdaxe-gamma",
            "version": "2.6.1",
            "macAddr": "AA:BB:CC:00:11:22",
            "customField": {"nested": True},
            "stratum": {"pools": [{"connected": True}]},
        }

        sample = normalize_miner_payload(
            payload,
            now=datetime(2026, 3, 10, 12, 0, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(sample.ts, "2026-03-10T12:00:00Z")
        self.assertEqual(sample.hash_rate, 812.5)
        self.assertEqual(sample.hash_rate_10m, 790.25)
        self.assertEqual(sample.temp, 58.2)
        self.assertEqual(sample.voltage, 5.0)
        self.assertEqual(sample.current, 2.5)
        self.assertEqual(sample.fan_rpm, 6200)
        self.assertEqual(sample.best_diff, 1_500_000_000)
        self.assertEqual(sample.best_session_diff, 250_000_000)
        self.assertEqual(sample.stratum_connected, True)
        self.assertEqual(sample.stable_device_id, "aa_bb_cc_00_11_22")
        self.assertEqual(sample.extra, {"customField": {"nested": True}})

    def test_nested_stratum_aliases_are_used(self) -> None:
        payload = {
            "stratum": {
                "pools": [
                    {
                        "connected": "online",
                        "accepted": 7,
                        "rejected": 2,
                        "bestDiff": "3K",
                    }
                ]
            }
        }

        sample = normalize_miner_payload(payload)

        self.assertEqual(sample.stratum_connected, True)
        self.assertEqual(sample.shares_accepted, 7)
        self.assertEqual(sample.shares_rejected, 2)
        self.assertEqual(sample.best_diff, 3000)

    def test_numeric_coercion_rejects_invalid_values(self) -> None:
        self.assertIsNone(to_float(True))
        self.assertIsNone(to_float("not-a-number"))
        self.assertIsNone(to_float(""))
        self.assertEqual(to_float("10.5"), 10.5)
        self.assertEqual(to_difficulty("2T"), 2_000_000_000_000)
        self.assertIsNone(to_difficulty("many"))

    def test_extra_sanitization_handles_non_json_values(self) -> None:
        value = sanitize_history_value(
            {
                "finite": 1,
                "nonFinite": float("inf"),
                "items": [1, float("nan"), object()],
            }
        )

        self.assertEqual(value["finite"], 1)
        self.assertIsNone(value["nonFinite"])
        self.assertEqual(value["items"][0], 1)
        self.assertIsNone(value["items"][1])
        self.assertIsInstance(value["items"][2], str)

    def test_stable_id_and_connected_helpers_return_none_when_unknown(self) -> None:
        self.assertIsNone(find_stable_device_id({"hostname": "not-stable"}))
        self.assertIsNone(infer_stratum_connected({"stratum": {}}))


if __name__ == "__main__":
    unittest.main()
