"""Button entities for NerdAxe Miner controls."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

from homeassistant.components.button import (
    ButtonDeviceClass,
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import MinerApiError
from .const import DOMAIN
from .coordinator import NerdAxeMinerCoordinator


@dataclass(frozen=True)
class NerdAxeButtonEntityDescription(ButtonEntityDescription):
    """Describes a NerdAxe button."""

    press_fn: Callable[[NerdAxeMinerCoordinator], Awaitable[None]] | None = None


BUTTON_DESCRIPTIONS: tuple[NerdAxeButtonEntityDescription, ...] = (
    NerdAxeButtonEntityDescription(
        key="restart",
        name="Restart",
        translation_key="restart",
        device_class=ButtonDeviceClass.RESTART,
        entity_category=EntityCategory.CONFIG,
        press_fn=lambda coordinator: coordinator.api.async_restart(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up NerdAxe Miner buttons."""

    coordinator: NerdAxeMinerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        NerdAxeButton(coordinator, description) for description in BUTTON_DESCRIPTIONS
    )


class NerdAxeButton(CoordinatorEntity[NerdAxeMinerCoordinator], ButtonEntity):
    """A NerdAxe Miner button."""

    entity_description: NerdAxeButtonEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NerdAxeMinerCoordinator,
        description: NerdAxeButtonEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.entity_unique_prefix}_{description.key}"
        self._attr_device_info = coordinator.device_info

    async def async_press(self) -> None:
        """Handle the button press."""

        if self.entity_description.press_fn is None:
            return

        try:
            await self.entity_description.press_fn(self.coordinator)
        except MinerApiError as err:
            raise HomeAssistantError(f"Failed to restart NerdAxe miner: {err}") from err
