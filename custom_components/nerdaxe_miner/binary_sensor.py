"""Binary sensor entities for NerdAxe Miner."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NerdAxeMinerCoordinator
from .models import MinerSample


@dataclass(frozen=True)
class NerdAxeBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes a NerdAxe binary sensor."""

    value_fn: Callable[[MinerSample], bool | None] | None = None


BINARY_SENSOR_DESCRIPTIONS: tuple[NerdAxeBinarySensorEntityDescription, ...] = (
    NerdAxeBinarySensorEntityDescription(
        key="stratum_connected",
        name="Stratum connected",
        translation_key="stratum_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda data: data.stratum_connected,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up NerdAxe Miner binary sensors."""

    coordinator: NerdAxeMinerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        NerdAxeBinarySensor(coordinator, description)
        for description in BINARY_SENSOR_DESCRIPTIONS
    )


class NerdAxeBinarySensor(
    CoordinatorEntity[NerdAxeMinerCoordinator],
    BinarySensorEntity,
):
    """A NerdAxe Miner binary sensor."""

    entity_description: NerdAxeBinarySensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NerdAxeMinerCoordinator,
        description: NerdAxeBinarySensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.entity_unique_prefix}_{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def is_on(self) -> bool | None:
        """Return true if the miner is connected to its pool."""

        if self.coordinator.data is None or self.entity_description.value_fn is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
