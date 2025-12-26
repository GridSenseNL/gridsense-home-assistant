"""Config flow for GridSense integration."""

from __future__ import annotations

from typing import Any
import logging
import re

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import zeroconf
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_HOST, DOMAIN
from .coordinator import async_fetch_devices

_LOGGER = logging.getLogger(__name__)


class GridSenseConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for GridSense."""

    VERSION = 1

    _discovered_host: str | None = None
    _discovered_name: str | None = None
    _discovered_gateway_id: str | None = None
    _discovered_unique_id: str | None = None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            for entry in self._async_current_entries():
                if entry.data.get(CONF_HOST) == host:
                    return self.async_abort(reason="already_configured")
            result = await self._async_validate_host(host)
            if result is None:
                unique_id = self._discovered_unique_id or host
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                gateway_identifier = self._gateway_identifier(host)
                title = f"GridSense Gateway {gateway_identifier}"
                return self.async_create_entry(title=title, data={CONF_HOST: host})
            errors["base"] = result

        data_schema = vol.Schema(
            {vol.Required(CONF_HOST, default=self._discovered_host or vol.UNDEFINED): str}
        )
        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

    async def async_step_zeroconf(
        self, discovery_info: zeroconf.ZeroconfServiceInfo
    ) -> FlowResult:
        """Handle discovery from mDNS."""
        host = discovery_info.host
        mdns_name = _normalize_mdns_name(discovery_info.hostname) or _normalize_mdns_name(
            discovery_info.name
        )
        self._discovered_gateway_id = _extract_gateway_id(mdns_name)
        self._discovered_unique_id = self._discovered_gateway_id or host
        self._discovered_host = host
        self._discovered_name = mdns_name

        for entry in self._async_current_entries():
            if entry.data.get(CONF_HOST) == host:
                return self.async_abort(reason="already_configured")

        await self.async_set_unique_id(self._discovered_unique_id)
        self._abort_if_unique_id_configured()

        gateway_identifier = self._gateway_identifier(host)
        self.context["title_placeholders"] = {"host": host, "name": gateway_identifier}
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Confirm adding the discovered device."""
        if user_input is not None:
            return await self.async_step_user({CONF_HOST: self._discovered_host})

        return self.async_show_form(
            step_id="confirm",
            description_placeholders={"host": self._discovered_host},
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        """Handle re-auth when connection fails."""
        self._discovered_host = entry_data.get(CONF_HOST)
        return await self.async_step_user()

    async def _async_validate_host(self, host: str) -> str | None:
        """Validate host by fetching data."""
        session = async_get_clientsession(self.hass)
        try:
            await async_fetch_devices(session, host)
        except Exception as err:  # noqa: BLE001 - broad on purpose for flow errors
            _LOGGER.debug("GridSense validation failed for %s: %s", host, err)
            return "cannot_connect"
        return None

    def _gateway_identifier(self, host: str) -> str:
        """Return a short identifier for the gateway."""
        if self._discovered_gateway_id:
            return self._discovered_gateway_id
        if self._discovered_name:
            extracted = _extract_gateway_id(self._discovered_name)
            if extracted:
                self._discovered_gateway_id = extracted
                return extracted
        return host


def _normalize_mdns_name(name: str | None) -> str | None:
    """Normalize mDNS name (remove trailing dot)."""
    if not name:
        return None
    return name.rstrip(".")


def _extract_gateway_id(mdns_name: str | None) -> str | None:
    """Extract the short gateway identifier from an mDNS hostname."""
    if not mdns_name:
        return None
    normalized = _normalize_mdns_name(mdns_name)
    if normalized is None:
        return None
    match = re.match(r"^gridsense-([a-zA-Z0-9]+)-homeassistant", normalized.lower())
    if match:
        return match.group(1)
    return None
