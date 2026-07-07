"""Number entities for NerdAxe Miner controls."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Awaitable, Callable

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import MinerApiError
from .const import (
    DOMAIN,
    FAN_SPEED_MAX,
    FAN_SPEED_MIN,
    PID_TARGET_TEMP_MAX,
    PID_TARGET_TEMP_MIN,
)
from .coordinator import NerdAxeMinerCoordinator
from .models import MinerSample


@dataclass(frozen=True)
class NerdAxeNumberEntityDescription(NumberEntityDescription):
    """Describes a NerdAxe number."""

    value_fn: Callable[[MinerSample], float | None] | None = None
    set_fn: Callable[[NerdAxeMinerCoordinator, int], Awaitable[None]] | None = None
    required_auto_fan_speed: bool | None = None


NUMBER_DESCRIPTIONS: tuple[NerdAxeNumberEntityDescription, ...] = (
    NerdAxeNumberEntityDescription(
        key="manual_fan_speed",
        name="Manual fan speed",
        translation_key="manual_fan_speed",
        native_min_value=FAN_SPEED_MIN,
        native_max_value=FAN_SPEED_MAX,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        mode=NumberMode.SLIDER,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data: data.manual_fan_speed,
        set_fn=lambda coordinator, value: coordinator.api.async_set_manual_fan_speed(
            value
        ),
        required_auto_fan_speed=False,
    ),
    NerdAxeNumberEntityDescription(
        key="pid_target_temperature",
        name="PID target temperature",
        translation_key="pid_target_temperature",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_min_value=PID_TARGET_TEMP_MIN,
        native_max_value=PID_TARGET_TEMP_MAX,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        mode=NumberMode.SLIDER,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data: data.pid_target_temp,
        set_fn=lambda coordinator, value: coordinator.api.async_set_pid_target_temp(
            value
        ),
        required_auto_fan_speed=True,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up NerdAxe Miner numbers."""

    coordinator: NerdAxeMinerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        NerdAxeNumber(coordinator, description) for description in NUMBER_DESCRIPTIONS
    )


def _coerce_integer_value(value: float) -> int:
    """Convert a Home Assistant number value to an integer setting."""

    if isinstance(value, bool):
        raise ValueError("value must be an integer")
    try:
        parsed = float(value)
    except (TypeError, ValueError) as err:
        raise ValueError("value must be an integer") from err
    if not math.isfinite(parsed) or not parsed.is_integer():
        raise ValueError("value must be a whole number")
    return int(parsed)


class NerdAxeNumber(CoordinatorEntity[NerdAxeMinerCoordinator], NumberEntity):
    """A NerdAxe Miner number."""

    entity_description: NerdAxeNumberEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NerdAxeMinerCoordinator,
        description: NerdAxeNumberEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.entity_unique_prefix}_{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> float | None:
        """Return the current number value."""

        if self.coordinator.data is None or self.entity_description.value_fn is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def available(self) -> bool:
        """Return true if the number can be used."""

        return (
            super().available
            and self.native_value is not None
            and self._fan_mode_matches()
        )

    async def async_set_native_value(self, value: float) -> None:
        """Set the number value."""

        if self.entity_description.set_fn is None:
            return
        if self.coordinator.data is None:
            raise HomeAssistantError("No NerdAxe miner data is available yet")
        if not self._fan_mode_matches():
            raise HomeAssistantError(self._mode_error_message())

        try:
            await self.entity_description.set_fn(
                self.coordinator,
                _coerce_integer_value(value),
            )
        except (MinerApiError, ValueError) as err:
            raise HomeAssistantError(
                f"Failed to update NerdAxe fan setting: {err}"
            ) from err

        await self.coordinator.async_request_refresh()

    def _fan_mode_matches(self) -> bool:
        """Return true if the miner is in the mode required by this entity."""

        required = self.entity_description.required_auto_fan_speed
        if required is None:
            return True
        if self.coordinator.data is None:
            return False
        return self.coordinator.data.auto_fan_speed == required

    def _mode_error_message(self) -> str:
        if self.entity_description.required_auto_fan_speed:
            return "PID target temperature can only be set in PID fan mode"
        return "Manual fan speed can only be set in Manual fan mode"
