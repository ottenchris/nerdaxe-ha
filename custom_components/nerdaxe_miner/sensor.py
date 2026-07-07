"""Sensor entities for NerdAxe Miner."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NerdAxeMinerCoordinator
from .models import MinerSample


@dataclass(frozen=True)
class NerdAxeSensorEntityDescription(SensorEntityDescription):
    """Describes a NerdAxe sensor."""

    value_fn: Callable[[MinerSample], Any] | None = None


SENSOR_DESCRIPTIONS: tuple[NerdAxeSensorEntityDescription, ...] = (
    NerdAxeSensorEntityDescription(
        key="hash_rate",
        name="Hashrate",
        translation_key="hash_rate",
        native_unit_of_measurement="GH/s",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda data: data.hash_rate,
    ),
    NerdAxeSensorEntityDescription(
        key="hash_rate_1m",
        name="Hashrate 1m",
        translation_key="hash_rate_1m",
        native_unit_of_measurement="GH/s",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda data: data.hash_rate_1m,
    ),
    NerdAxeSensorEntityDescription(
        key="hash_rate_10m",
        name="Hashrate 10m",
        translation_key="hash_rate_10m",
        native_unit_of_measurement="GH/s",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda data: data.hash_rate_10m,
    ),
    NerdAxeSensorEntityDescription(
        key="hash_rate_1h",
        name="Hashrate 1h",
        translation_key="hash_rate_1h",
        native_unit_of_measurement="GH/s",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda data: data.hash_rate_1h,
    ),
    NerdAxeSensorEntityDescription(
        key="hash_rate_1d",
        name="Hashrate 1d",
        translation_key="hash_rate_1d",
        native_unit_of_measurement="GH/s",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda data: data.hash_rate_1d,
    ),
    NerdAxeSensorEntityDescription(
        key="asic_temperature",
        name="ASIC temperature",
        translation_key="asic_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.temp,
    ),
    NerdAxeSensorEntityDescription(
        key="vr_temperature",
        name="VR temperature",
        translation_key="vr_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.vr_temp,
    ),
    NerdAxeSensorEntityDescription(
        key="power",
        name="Power",
        translation_key="power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda data: data.power,
    ),
    NerdAxeSensorEntityDescription(
        key="voltage",
        name="Voltage",
        translation_key="voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=lambda data: data.voltage,
    ),
    NerdAxeSensorEntityDescription(
        key="current",
        name="Current",
        translation_key="current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=lambda data: data.current,
    ),
    NerdAxeSensorEntityDescription(
        key="fan_percent",
        name="Fan",
        translation_key="fan_percent",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda data: data.fan_percent,
    ),
    NerdAxeSensorEntityDescription(
        key="fan_rpm",
        name="Fan RPM",
        translation_key="fan_rpm",
        native_unit_of_measurement="rpm",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda data: data.fan_rpm,
    ),
    NerdAxeSensorEntityDescription(
        key="overheat_temperature",
        name="Overheat temperature",
        translation_key="overheat_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.overheat_temp,
    ),
    NerdAxeSensorEntityDescription(
        key="shares_accepted",
        name="Shares accepted",
        translation_key="shares_accepted",
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=0,
        value_fn=lambda data: data.shares_accepted,
    ),
    NerdAxeSensorEntityDescription(
        key="shares_rejected",
        name="Shares rejected",
        translation_key="shares_rejected",
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=0,
        value_fn=lambda data: data.shares_rejected,
    ),
    NerdAxeSensorEntityDescription(
        key="best_diff",
        name="Best diff",
        translation_key="best_diff",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda data: data.best_diff,
    ),
    NerdAxeSensorEntityDescription(
        key="best_session_diff",
        name="Best session diff",
        translation_key="best_session_diff",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda data: data.best_session_diff,
    ),
    NerdAxeSensorEntityDescription(
        key="wifi_rssi",
        name="Wi-Fi RSSI",
        translation_key="wifi_rssi",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement="dBm",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.wifi_rssi,
    ),
    NerdAxeSensorEntityDescription(
        key="frequency",
        name="Frequency",
        translation_key="frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        native_unit_of_measurement="MHz",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda data: data.frequency,
    ),
    NerdAxeSensorEntityDescription(
        key="actual_frequency",
        name="Actual frequency",
        translation_key="actual_frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        native_unit_of_measurement="MHz",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.actual_frequency,
    ),
    NerdAxeSensorEntityDescription(
        key="default_frequency",
        name="Default frequency",
        translation_key="default_frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        native_unit_of_measurement="MHz",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.default_frequency,
    ),
    NerdAxeSensorEntityDescription(
        key="core_voltage",
        name="Core voltage",
        translation_key="core_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement="mV",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda data: data.core_voltage,
    ),
    NerdAxeSensorEntityDescription(
        key="core_voltage_actual",
        name="Actual core voltage",
        translation_key="core_voltage_actual",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement="mV",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda data: data.core_voltage_actual,
    ),
    NerdAxeSensorEntityDescription(
        key="default_core_voltage",
        name="Default core voltage",
        translation_key="default_core_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement="mV",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.default_core_voltage,
    ),
    NerdAxeSensorEntityDescription(
        key="uptime",
        name="Uptime",
        translation_key="uptime",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.uptime_seconds,
    ),
    NerdAxeSensorEntityDescription(
        key="last_boot",
        name="Last boot",
        translation_key="last_boot",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.last_boot,
    ),
    NerdAxeSensorEntityDescription(
        key="firmware_version",
        name="Firmware version",
        translation_key="firmware_version",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.firmware_version,
    ),
    NerdAxeSensorEntityDescription(
        key="hostname",
        name="Hostname",
        translation_key="hostname",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.hostname,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up NerdAxe Miner sensors."""

    coordinator: NerdAxeMinerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        NerdAxeSensor(coordinator, description) for description in SENSOR_DESCRIPTIONS
    )


class NerdAxeSensor(CoordinatorEntity[NerdAxeMinerCoordinator], SensorEntity):
    """A NerdAxe Miner sensor."""

    entity_description: NerdAxeSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NerdAxeMinerCoordinator,
        description: NerdAxeSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.entity_unique_prefix}_{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""

        if self.coordinator.data is None or self.entity_description.value_fn is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
