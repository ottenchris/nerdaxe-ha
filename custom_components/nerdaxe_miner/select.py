"""Select entities for NerdAxe Miner controls."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import MinerApiError
from .const import DOMAIN
from .coordinator import NerdAxeMinerCoordinator
from .models import MinerSample

FAN_MODE_PID = "PID"
FAN_MODE_MANUAL = "Manual"
FAN_MODE_OPTIONS = [FAN_MODE_PID, FAN_MODE_MANUAL]


@dataclass(frozen=True)
class NerdAxeSelectEntityDescription(SelectEntityDescription):
    """Describes a NerdAxe select."""

    options: list[str] | None = None
    value_fn: Callable[[MinerSample], str | None] | None = None
    select_fn: Callable[[NerdAxeMinerCoordinator, str], Awaitable[None]] | None = None


async def _async_select_fan_control_mode(
    coordinator: NerdAxeMinerCoordinator,
    option: str,
) -> None:
    if option == FAN_MODE_PID:
        await coordinator.api.async_set_fan_control_mode(True)
        return
    if option == FAN_MODE_MANUAL:
        await coordinator.api.async_set_fan_control_mode(False)
        return
    raise ValueError(f"unsupported fan control mode: {option}")


SELECT_DESCRIPTIONS: tuple[NerdAxeSelectEntityDescription, ...] = (
    NerdAxeSelectEntityDescription(
        key="fan_control_mode",
        name="Fan control mode",
        translation_key="fan_control_mode",
        options=FAN_MODE_OPTIONS,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data: (
            (FAN_MODE_PID if data.auto_fan_speed else FAN_MODE_MANUAL)
            if data.auto_fan_speed is not None
            else None
        ),
        select_fn=_async_select_fan_control_mode,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up NerdAxe Miner selects."""

    coordinator: NerdAxeMinerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        NerdAxeSelect(coordinator, description) for description in SELECT_DESCRIPTIONS
    )


class NerdAxeSelect(CoordinatorEntity[NerdAxeMinerCoordinator], SelectEntity):
    """A NerdAxe Miner select."""

    entity_description: NerdAxeSelectEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NerdAxeMinerCoordinator,
        description: NerdAxeSelectEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.entity_unique_prefix}_{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""

        if self.coordinator.data is None or self.entity_description.value_fn is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def options(self) -> list[str]:
        """Return the available options."""

        return self.entity_description.options or []

    @property
    def available(self) -> bool:
        """Return true if the select can be used."""

        return super().available and self.current_option is not None

    async def async_select_option(self, option: str) -> None:
        """Set the selected option."""

        if self.entity_description.select_fn is None:
            return

        try:
            await self.entity_description.select_fn(self.coordinator, option)
        except (MinerApiError, ValueError) as err:
            raise HomeAssistantError(
                f"Failed to update NerdAxe fan control mode: {err}"
            ) from err

        await self.coordinator.async_request_refresh()
