from __future__ import annotations

import unittest
from typing import Any

try:
    from custom_components.nerdaxe_miner.coordinator import NerdAxeMinerCoordinator
except ModuleNotFoundError as err:
    if err.name == "homeassistant":
        raise unittest.SkipTest("Home Assistant is not installed") from err
    raise


class FakeApi:
    def __init__(self) -> None:
        self.get_info_calls = 0
        self.restart_calls = 0
        self.fan_control_mode_calls = 0
        self.manual_fan_speed_calls = 0
        self.pid_target_temp_calls = 0

    async def async_get_info(self) -> dict[str, Any]:
        self.get_info_calls += 1
        return {"hashRate": 123.4, "hostname": "miner-one"}

    async def async_restart(self) -> None:
        self.restart_calls += 1

    async def async_set_fan_control_mode(self, _auto: bool) -> None:
        self.fan_control_mode_calls += 1

    async def async_set_manual_fan_speed(self, _percent: int) -> None:
        self.manual_fan_speed_calls += 1

    async def async_set_pid_target_temp(self, _celsius: int) -> None:
        self.pid_target_temp_calls += 1


class CoordinatorPollingTest(unittest.IsolatedAsyncioTestCase):
    async def test_update_data_only_reads_system_info(self) -> None:
        coordinator = object.__new__(NerdAxeMinerCoordinator)
        api = FakeApi()
        coordinator.api = api
        coordinator._history_store = None

        sample = await coordinator._async_update_data()

        self.assertEqual(sample.hash_rate, 123.4)
        self.assertEqual(api.get_info_calls, 1)
        self.assertEqual(api.restart_calls, 0)
        self.assertEqual(api.fan_control_mode_calls, 0)
        self.assertEqual(api.manual_fan_speed_calls, 0)
        self.assertEqual(api.pid_target_temp_calls, 0)


if __name__ == "__main__":
    unittest.main()
