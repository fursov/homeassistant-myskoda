"""Climate entities for MySkoda."""

import logging

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityDescription,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType
from myskoda.models.air_conditioning import AirConditioning
from myskoda.models.info import CapabilityId

from .const import COORDINATORS, DOMAIN
from .coordinator import MySkodaDataUpdateCoordinator
from .entity import MySkodaEntity
from .utils import InvalidCapabilityConfigurationError, add_supported_entities

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    add_supported_entities(
        available_entities=[MySkodaClimate],
        coordinators=hass.data[DOMAIN][config.entry_id][COORDINATORS],
        async_add_entities=async_add_entities,
    )


class MySkodaClimate(MySkodaEntity, ClimateEntity):
    """Climate control for MySkoda vehicles."""

    entity_description = ClimateEntityDescription(
        key="climate",
        name="Air Conditioning",
        icon="mdi:air-conditioner",
        translation_key="climate",
    )
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    def __init__(self, coordinator: MySkodaDataUpdateCoordinator, vin: str) -> None:  # noqa: D107
        super().__init__(
            coordinator,
            vin,
        )
        ClimateEntity.__init__(self)

    def _air_conditioning(self) -> AirConditioning:
        air_conditioning = self.vehicle.air_conditioning
        if air_conditioning is None:
            raise InvalidCapabilityConfigurationError(
                self.entity_description.key, self.vehicle
            )
        return air_conditioning

    @property
    def hvac_modes(self) -> list[HVACMode]:  # noqa: D102
        return [HVACMode.AUTO, HVACMode.OFF]

    @property
    def hvac_mode(self) -> HVACMode | None:  # noqa: D102
        if self._air_conditioning().state:
            return HVACMode.AUTO
        return HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction | None:  # noqa: D102
        if self._air_conditioning().state == "HEATING":
            return HVACAction.HEATING
        if self._air_conditioning().state == "COOLING":
            return HVACAction.COOLING
        return HVACAction.OFF

    @property
    def target_temperature(self) -> None | float:  # noqa: D102
        target_temperature = self._air_conditioning().target_temperature
        if target_temperature is None:
            return None
        return target_temperature.temperature_value

    async def async_set_hvac_mode(self, hvac_mode: HVACMode):  # noqa: D102
        target_temperature = self._air_conditioning().target_temperature
        if target_temperature is None:
            return None

        if hvac_mode == HVACMode.AUTO:
            await self.coordinator.myskoda.start_air_conditioning(
                self.vehicle.info.vin,
                target_temperature.temperature_value,
            )
        else:
            await self.coordinator.myskoda.stop_air_conditioning(self.vehicle.info.vin)
        _LOGGER.info("HVAC mode set to %s.", hvac_mode)

    async def async_turn_on(self):  # noqa: D102
        await self.async_set_hvac_mode(HVACMode.AUTO)

    async def async_turn_off(self):  # noqa: D102
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_set_temperature(self, **kwargs):  # noqa: D102
        temp = kwargs[ATTR_TEMPERATURE]
        await self.coordinator.myskoda.set_target_temperature(
            self.vehicle.info.vin, temp
        )
        _LOGGER.info("AC disabled.")

    def required_capabilities(self) -> list[CapabilityId]:
        return [
            CapabilityId.AIR_CONDITIONING,
            CapabilityId.AIR_CONDITIONING_SAVE_AND_ACTIVATE,
        ]