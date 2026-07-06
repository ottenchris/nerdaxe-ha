from __future__ import annotations

import unittest

try:
    import voluptuous as vol
except ModuleNotFoundError as err:
    raise unittest.SkipTest(
        "Home Assistant test dependencies are not installed"
    ) from err

try:
    import homeassistant  # noqa: F401
except ModuleNotFoundError as err:
    raise unittest.SkipTest("Home Assistant is not installed") from err

from custom_components.nerdaxe_miner import binary_sensor, config_flow, sensor
from custom_components.nerdaxe_miner.const import (
    CONF_HISTORY_ENABLED,
    CONF_HISTORY_MAX_MB,
    CONF_HISTORY_RAW_KEEP_DAYS,
    CONF_HISTORY_STORE_RAW_PAYLOAD,
    CONF_SCAN_INTERVAL,
)


class HomeAssistantImportTest(unittest.TestCase):
    def test_ha_modules_import(self) -> None:
        self.assertTrue(sensor.SENSOR_DESCRIPTIONS)
        self.assertTrue(binary_sensor.BINARY_SENSOR_DESCRIPTIONS)
        self.assertTrue(config_flow.NerdAxeMinerConfigFlow)

    def test_options_schema_rejects_scan_interval_below_minimum(self) -> None:
        schema = config_flow._options_schema({})

        with self.assertRaises(vol.Invalid):
            schema(
                {
                    CONF_SCAN_INTERVAL: 1,
                    CONF_HISTORY_ENABLED: True,
                    CONF_HISTORY_MAX_MB: 512,
                    CONF_HISTORY_RAW_KEEP_DAYS: 30,
                    CONF_HISTORY_STORE_RAW_PAYLOAD: False,
                }
            )


if __name__ == "__main__":
    unittest.main()
