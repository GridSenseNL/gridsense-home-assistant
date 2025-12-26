"""Sensor platform for GridSense."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfEnergy, UnitOfPower, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import GridSenseDataUpdateCoordinator


@dataclass
class GridSenseSensorEntityDescription(SensorEntityDescription):
    """Describes a GridSense sensor entity."""

    value_fn: Callable[[dict[str, Any]], float | int | None] | None = None


class GridSenseSensor(CoordinatorEntity[GridSenseDataUpdateCoordinator], SensorEntity):
    """Representation of a GridSense sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: GridSenseDataUpdateCoordinator,
        device_name: str,
        unique_id: str,
        description: GridSenseSensorEntityDescription,
        device_info: DeviceInfo,
        data_getter: Callable[[dict[str, Any]], dict[str, Any] | None],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_device_info = device_info
        self._attr_unique_id = unique_id
        self._data_getter = data_getter
        self._attr_name = description.name or device_name
        # Explicitly expose unit/device/state classes to ensure UI shows units.
        self._attr_native_unit_of_measurement = description.native_unit_of_measurement
        self._attr_device_class = description.device_class
        self._attr_state_class = description.state_class

    @property
    def available(self) -> bool:
        """Return entity availability."""
        return super().available and self._data_getter(self.coordinator.data or {}) is not None

    @property
    def native_value(self) -> float | int | None:
        """Return the sensor value."""
        data = self._data_getter(self.coordinator.data or {})
        if data is None or self.entity_description.value_fn is None:
            return None
        return self.entity_description.value_fn(data)


INVERTER_SENSORS: tuple[GridSenseSensorEntityDescription, ...] = (
    GridSenseSensorEntityDescription(
        key="power_ac",
        name="AC Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: _try_float(data.get("powerAc")),
    ),
    GridSenseSensorEntityDescription(
        key="power_dc",
        name="DC Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: _try_float(data.get("powerDc")),
    ),
    GridSenseSensorEntityDescription(
        key="energy_injected_total",
        name="Energy Injected",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: _to_kwh(data.get("totalEnergyInjected")),
    ),
    GridSenseSensorEntityDescription(
        key="heatsink_temperature",
        name="Heatsink Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: _try_float(data.get("temperatureHeatsink")),
    ),
)


BATTERY_SENSORS: tuple[GridSenseSensorEntityDescription, ...] = (
    GridSenseSensorEntityDescription(
        key="power_dc",
        name="Battery Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: _try_float(data.get("powerDc")),
    ),
    GridSenseSensorEntityDescription(
        key="state_of_energy",
        name="State of Energy",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: _to_percentage(data.get("soe")),
    ),
    GridSenseSensorEntityDescription(
        key="available_energy",
        name="Available Energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: _to_kwh(data.get("availableEnergy")),
    ),
)


GRID_METER_SENSORS: tuple[GridSenseSensorEntityDescription, ...] = (
    GridSenseSensorEntityDescription(
        key="grid_power",
        name="Grid Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: _try_float(data.get("powerAc")),
    ),
    GridSenseSensorEntityDescription(
        key="grid_import_total",
        name="Imported Energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: _to_kwh(data.get("totalImportAc")),
    ),
    GridSenseSensorEntityDescription(
        key="grid_export_total",
        name="Exported Energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: _to_kwh(data.get("totalExportAc")),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up GridSense sensors based on a config entry."""
    coordinator: GridSenseDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[GridSenseSensor] = []
    data = coordinator.data or {}
    inverters = list((data.get("inverters") or {}).values())

    for inverter in inverters:
        inverter_manufacturer = _identifier(inverter.get("manufacturer"), "unknown_manufacturer")
        inverter_serial = _identifier(inverter.get("serialNumber"), "unknown_serial")
        if not inverter_serial:
            continue
        inverter_model = inverter.get("model") or "Inverter"

        inverter_device = DeviceInfo(
            identifiers={(DOMAIN, f"inverter_{inverter_manufacturer}_{inverter_serial}")},
            manufacturer=inverter_manufacturer or "GridSense",
            model=inverter_model,
            name=inverter_model,
            sw_version=inverter.get("version"),
        )

        for description in INVERTER_SENSORS:
            entities.append(
                GridSenseSensor(
                    coordinator=coordinator,
                    device_name=inverter_model,
                    unique_id=f"{inverter_manufacturer}_{inverter_serial}_{description.key}",
                    description=description,
                    device_info=inverter_device,
                    data_getter=lambda payload, inv_man=inverter_manufacturer, inv_serial=inverter_serial: _find_inverter(
                        payload, inv_man, inv_serial
                    ),
                )
            )

        for index, battery in enumerate(
            _find_batteries_for_inverter(data, inverter_manufacturer, inverter_serial)
        ):
            battery_manufacturer = _identifier(battery.get("manufacturer"), "unknown_manufacturer")
            battery_serial = _identifier(
                battery.get("serialNumber"), f"{inverter_serial}_b{index}"
            )
            battery_model = battery.get("model") or "Battery"

            battery_device = DeviceInfo(
                identifiers={(DOMAIN, f"battery_{battery_manufacturer}_{battery_serial}")},
                manufacturer=battery_manufacturer or "GridSense",
                model=battery_model,
                name=battery_model,
                sw_version=battery.get("version"),
                via_device=(DOMAIN, f"inverter_{inverter_manufacturer}_{inverter_serial}"),
            )

            for description in BATTERY_SENSORS:
                entities.append(
                    GridSenseSensor(
                        coordinator=coordinator,
                        device_name=battery_model,
                        unique_id=f"{battery_manufacturer}_{battery_serial}_{description.key}",
                        description=description,
                        device_info=battery_device,
                        data_getter=lambda payload, inv_man=inverter_manufacturer, inv_serial=inverter_serial, bat_man=battery_manufacturer, bat_serial=battery_serial: _find_battery(
                            payload, inv_man, inv_serial, bat_man, bat_serial
                        ),
                    )
                )

        meter_index = 0
        for meter in _find_meters_for_inverter(data, inverter_manufacturer, inverter_serial):
            if not _is_import_export_meter(meter):
                continue
            meter_manufacturer = _identifier(meter.get("manufacturer"), "unknown_manufacturer")
            meter_serial = _identifier(
                meter.get("serialNumber"), f"{inverter_serial}_m{meter_index}"
            )
            meter_index += 1
            meter_model = meter.get("model") or "Energy Meter"

            meter_device = DeviceInfo(
                identifiers={(DOMAIN, f"meter_{meter_manufacturer}_{meter_serial}")},
                manufacturer=meter_manufacturer or "GridSense",
                model=meter_model,
                name=meter_model,
                sw_version=meter.get("version"),
                via_device=(DOMAIN, f"inverter_{inverter_manufacturer}_{inverter_serial}"),
            )

            for description in GRID_METER_SENSORS:
                entities.append(
                    GridSenseSensor(
                        coordinator=coordinator,
                        device_name=meter_model,
                        unique_id=f"{meter_manufacturer}_{meter_serial}_{description.key}",
                        description=description,
                        device_info=meter_device,
                        data_getter=lambda payload, inv_man=inverter_manufacturer, inv_serial=inverter_serial, met_man=meter_manufacturer, met_serial=meter_serial: _find_meter(
                            payload, inv_man, inv_serial, met_man, met_serial
                        ),
                    )
                )

    async_add_entities(entities)


def _identifier(candidate: str | None, fallback: str = "") -> str:
    """Normalize strings that may contain padding."""
    if not candidate:
        return fallback
    cleaned = candidate.replace("\x00", "").strip()
    return cleaned or fallback


def _try_float(value: Any) -> float | int | None:
    """Convert a value to float when possible."""
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _to_kwh(value: Any) -> float | None:
    """Convert watt-hours to kiloWatt-hours."""
    numeric = _try_float(value)
    if numeric is None:
        return None
    return numeric / 1000


def _to_percentage(value: Any) -> float | None:
    """Return percentage value as provided by the API."""
    numeric = _try_float(value)
    if numeric is None:
        return None
    return numeric


def _find_inverter(payload: dict[str, Any] | None, manufacturer: str, serial: str) -> dict[str, Any] | None:
    """Find inverter by manufacturer and serial."""
    for inverter in (payload or {}).get("inverters", {}).values():
        if _identifier(inverter.get("manufacturer"), "unknown_manufacturer") == manufacturer and _identifier(
            inverter.get("serialNumber"), "unknown_serial"
        ) == serial:
            return inverter
    return None


def _find_batteries_for_inverter(
    payload: dict[str, Any] | None, inverter_manufacturer: str, inverter_serial: str
) -> list[dict[str, Any]]:
    """Return batteries attached to a given inverter."""
    if payload is None:
        return []
    inverters = payload.get("inverters") or {}
    batteries = payload.get("batteries") or {}
    result: list[dict[str, Any]] = []

    for inverter_key, battery_list in batteries.items():
        inverter = inverters.get(inverter_key)
        if inverter is None:
            continue
        if _identifier(inverter.get("manufacturer"), "unknown_manufacturer") != inverter_manufacturer or _identifier(
            inverter.get("serialNumber"), "unknown_serial"
        ) != inverter_serial:
            continue
        result.extend(battery_list or [])
    return result


def _find_battery(
    payload: dict[str, Any] | None,
    inverter_manufacturer: str,
    inverter_serial: str,
    battery_manufacturer: str,
    battery_serial: str,
) -> dict[str, Any] | None:
    """Find battery matching inverter + manufacturer + serial."""
    for battery in _find_batteries_for_inverter(payload, inverter_manufacturer, inverter_serial):
        if _identifier(battery.get("manufacturer"), battery_manufacturer) == battery_manufacturer and _identifier(
            battery.get("serialNumber"), battery_serial
        ) == battery_serial:
            return battery
    return None


def _find_meters_for_inverter(
    payload: dict[str, Any] | None, inverter_manufacturer: str, inverter_serial: str
) -> list[dict[str, Any]]:
    """Return energy meters attached to a given inverter."""
    if payload is None:
        return []
    inverters = payload.get("inverters") or {}
    meters = payload.get("energyMeters") or {}
    result: list[dict[str, Any]] = []

    for inverter_key, meter_list in meters.items():
        inverter = inverters.get(inverter_key)
        if inverter is None:
            continue
        if _identifier(inverter.get("manufacturer"), "unknown_manufacturer") != inverter_manufacturer or _identifier(
            inverter.get("serialNumber"), "unknown_serial"
        ) != inverter_serial:
            continue
        result.extend(meter_list or [])
    return result


def _find_meter(
    payload: dict[str, Any] | None,
    inverter_manufacturer: str,
    inverter_serial: str,
    meter_manufacturer: str,
    meter_serial: str,
) -> dict[str, Any] | None:
    """Find energy meter matching inverter + manufacturer + serial."""
    for meter in _find_meters_for_inverter(payload, inverter_manufacturer, inverter_serial):
        if _identifier(meter.get("manufacturer"), meter_manufacturer) == meter_manufacturer and _identifier(
            meter.get("serialNumber"), meter_serial
        ) == meter_serial:
            return meter
    return None


def _is_import_export_meter(meter: dict[str, Any]) -> bool:
    """Return True if meter reports import/export totals."""
    option = meter.get("options")
    return isinstance(option, str) and "export+import" in option.lower()
