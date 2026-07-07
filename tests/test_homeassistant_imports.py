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

from homeassistant.components.button import ButtonDeviceClass
from homeassistant.components.number import NumberDeviceClass

from custom_components.nerdaxe_miner import (
    binary_sensor,
    button,
    config_flow,
    number,
    sensor,
)
from custom_components.nerdaxe_miner import (
    select as fan_select,
)
from custom_components.nerdaxe_miner.const import (
    CONF_HISTORY_ENABLED,
    CONF_HISTORY_MAX_MB,
    CONF_HISTORY_RAW_KEEP_DAYS,
    CONF_HISTORY_STORE_RAW_PAYLOAD,
    CONF_SCAN_INTERVAL,
    DEFAULT_HISTORY_ENABLED,
)


class HomeAssistantImportTest(unittest.TestCase):
    def test_ha_modules_import(self) -> None:
        self.assertTrue(sensor.SENSOR_DESCRIPTIONS)
        self.assertTrue(binary_sensor.BINARY_SENSOR_DESCRIPTIONS)
        self.assertTrue(button.BUTTON_DESCRIPTIONS)
        self.assertTrue(fan_select.SELECT_DESCRIPTIONS)
        self.assertTrue(number.NUMBER_DESCRIPTIONS)
        self.assertTrue(config_flow.NerdAxeMinerConfigFlow)

    def test_button_restart_description_uses_restart_device_class(self) -> None:
        description = button.BUTTON_DESCRIPTIONS[0]

        self.assertEqual(description.key, "restart")
        self.assertEqual(description.device_class, ButtonDeviceClass.RESTART)

    def test_fan_control_entities_replace_read_only_control_state(self) -> None:
        sensor_keys = {description.key for description in sensor.SENSOR_DESCRIPTIONS}
        binary_sensor_keys = {
            description.key for description in binary_sensor.BINARY_SENSOR_DESCRIPTIONS
        }
        select_keys = {
            description.key for description in fan_select.SELECT_DESCRIPTIONS
        }
        number_keys = {description.key for description in number.NUMBER_DESCRIPTIONS}

        self.assertNotIn("manual_fan_speed", sensor_keys)
        self.assertNotIn("pid_target_temperature", sensor_keys)
        self.assertNotIn("auto_fan_speed", binary_sensor_keys)
        self.assertIn("fan_control_mode", select_keys)
        self.assertIn("manual_fan_speed", number_keys)
        self.assertIn("pid_target_temperature", number_keys)
        self.assertIn("default_frequency", sensor_keys)
        self.assertIn("default_core_voltage", sensor_keys)
        self.assertIn("last_boot", sensor_keys)

    def test_fan_control_ranges_are_conservative(self) -> None:
        descriptions = {
            description.key: description for description in number.NUMBER_DESCRIPTIONS
        }

        manual_fan_speed = descriptions["manual_fan_speed"]
        self.assertEqual(manual_fan_speed.native_min_value, 20)
        self.assertEqual(manual_fan_speed.native_max_value, 100)

        pid_target_temperature = descriptions["pid_target_temperature"]
        self.assertEqual(
            pid_target_temperature.device_class,
            NumberDeviceClass.TEMPERATURE,
        )
        self.assertEqual(pid_target_temperature.native_min_value, 50)
        self.assertEqual(pid_target_temperature.native_max_value, 66)

    def test_fan_control_mode_mapping_is_explicit(self) -> None:
        description = fan_select.SELECT_DESCRIPTIONS[0]
        number_descriptions = {item.key: item for item in number.NUMBER_DESCRIPTIONS}

        self.assertEqual(description.options, ["PID", "Manual"])
        self.assertEqual(
            number_descriptions["manual_fan_speed"].required_auto_fan_speed,
            False,
        )
        self.assertEqual(
            number_descriptions["pid_target_temperature"].required_auto_fan_speed,
            True,
        )

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

    def test_options_schema_defaults_to_history_disabled(self) -> None:
        schema = config_flow._options_schema({})

        options = schema({})

        self.assertFalse(DEFAULT_HISTORY_ENABLED)
        self.assertFalse(options[CONF_HISTORY_ENABLED])


if __name__ == "__main__":
    unittest.main()
