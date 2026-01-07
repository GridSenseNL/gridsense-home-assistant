# GridSense — Home Assistant integration

A Home Assistant custom integration to integrate GridSense local energy sensors.

## Features
- Local polling of GridSense sensors
- Config flow (UI setup)
- Multiple sensors exposed to Home Assistant

## Prerequisites
- Home Assistant core (recommended minimum): 2025.3.0
- HACS installed (recommended) or manual installation (below)
- If hosted on GitHub, a release (tag) is required for HACS to pick up versions

## Installation via HACS (recommended)
<a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=GridSenseNL&repository=gridsense-home-assistant&category=integration" target="_blank"><img src="https://my.home-assistant.io/badges/hacs_repository.svg" alt="Open your Home Assistant instance and open a repository inside the Home Assistant Community Store." /></a>

1. Open Home Assistant UI → Settings → Integrations → Add Integration (or go to HACS if already installed).
2. If you already added this repository to your HACS custom repositories, search for "GridSense" in HACS → Integrations and install.
3. If not yet added to HACS automatically: HACS → Integrations → ⋯ (top-right) → Custom repositories → paste the repository URL, set category to "Integration", and click "Add".
4. After adding, install the integration from HACS → Integrations.
5. Restart Home Assistant if prompted.

## Manual installation
1. Download/clone this repository.
2. Copy the `custom_components/gridsense` folder into your Home Assistant `config/custom_components/` directory.
3. Restart Home Assistant.
4. Use Settings → Devices & Services → Add Integration and search for "GridSense" and follow the UI setup.

## Configuration
<a href="https://my.home-assistant.io/redirect/config_flow_start/?domain=gridsense" target="_blank"><img src="https://my.home-assistant.io/badges/config_flow_start.svg" alt="Open your Home Assistant instance and start setting up a new integration." /></a>

This integration uses the UI config flow. After installation:
- Go to Settings → Devices & Services → Add Integration → search for "GridSense".
- Follow the on-screen prompts to add your GridSense device.

There is no YAML configuration required by default. (If you add YAML options later, document them here.)

## Releases and tagging (for maintainers)
HACS discovers releases by tags. To create a release so HACS can pick it up:
1. Update `custom_components/gridsense/manifest.json` version field (recommended): e.g. "version": "0.1.1".
2. Commit and push your changes.
3. Create a Git tag and a GitHub Release (or release on your hosting provider): tag name should be `vMAJOR.MINOR.PATCH`, for example `v0.1.1`.
4. Create a release in GitHub using that tag and add release notes. HACS will detect the new release and the integration will appear/offer an update in HACS.
