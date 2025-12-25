"""Data update coordinator for GridSense."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

from aiohttp import ClientError, ClientSession
import async_timeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_PORT, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_fetch_devices(
    session: ClientSession, host: str, *, timeout: float = 15.0
) -> dict[str, Any]:
    """Fetch device data from the GridSense Gateway."""
    url = f"http://{host}:{DEFAULT_PORT}/api/v1/devices"
    try:
        async with async_timeout.timeout(timeout):
            response = await session.get(url)
            response.raise_for_status()
            payload = await response.json()
    except asyncio.TimeoutError as err:
        raise UpdateFailed(f"GridSense Gateway at {host} timed out") from err
    except ClientError as err:
        raise UpdateFailed(f"Error communicating with GridSense Gateway at {host}") from err
    except ValueError as err:
        raise UpdateFailed("Invalid JSON response from GridSense Gateway") from err

    if not isinstance(payload, dict):
        raise UpdateFailed("Unexpected payload from GridSense Gateway")

    return _sanitize_payload(payload)


class GridSenseDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to poll GridSense Gateway state."""

    def __init__(self, hass: HomeAssistant, host: str) -> None:
        """Initialize the coordinator."""
        self.host = host
        self._session = async_get_clientsession(hass)

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} ({host})",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the API endpoint."""
        return await async_fetch_devices(self._session, self.host)


def _sanitize_payload(value: Any) -> Any:
    """Recursively remove null padding and strip whitespace."""
    if isinstance(value, dict):
        return {key: _sanitize_payload(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize_payload(item) for item in value]
    if isinstance(value, str):
        return value.replace("\x00", "").strip()
    return value
