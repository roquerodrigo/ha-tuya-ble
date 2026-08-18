# Tuya BLE

[![CI](https://github.com/roquerodrigo/ha-tuya-ble/actions/workflows/ci.yml/badge.svg)](https://github.com/roquerodrigo/ha-tuya-ble/actions/workflows/ci.yml)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

[![Open your Home Assistant instance and open the repository inside HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=roquerodrigo&repository=ha-tuya-ble&category=integration)

---

Home Assistant integration for **Tuya Bluetooth Low Energy devices**. It talks to
the device directly over BLE — through the local adapter or any Bluetooth proxy
Home Assistant already has — and never contacts the Tuya cloud at runtime.

The protocol lives in a separate package,
[`tuya-ble-sdk`](https://github.com/roquerodrigo/tuya-ble-sdk).

## Supported devices

| Product ID | Device | Entities |
| --- | --- | --- |
| `gvygg3m8` | Soil sensor (SGS01) | soil moisture, temperature, battery level, battery state |

A device broadcasts its product id in the advertisement, so that is what
discovery matches on and what a new device is added by: supporting one more is
a table entry, not a new platform.

## How it reads the device

These sensors are battery powered and sleep between advertisements — they only
listen for a moment after announcing themselves. Home Assistant therefore
triggers a reading **when the device advertises**, not on a timer, and the
polling interval in the integration's options is the *minimum* spacing between
two readings (15 minutes by default). Each reading is one short connection:
handshake, one report, disconnect.

## Requirements

- A Bluetooth adapter or an [ESPHome Bluetooth proxy](https://esphome.io/components/bluetooth_proxy.html)
  in range of the device, with **active connections** enabled — values are read
  over a GATT connection, not from the advertisement.
- The device's `device_id` and `local_key`. Both come from the Tuya account that
  owns the device; the `uuid` and `product_id` are read from the advertisement,
  so they are not asked for.

## Installation

1. Add this repository to HACS as a custom repository (category *Integration*).
2. Install **Tuya BLE** and restart Home Assistant.
3. The device is discovered automatically once it advertises; confirm the
   discovery and fill in `device_id` and `local_key`.

## Not finished yet

- The artwork under `custom_components/tuya_ble/brand/` is still the
  blueprint's `TODO` placeholder and has not been submitted to
  [home-assistant/brands](https://github.com/home-assistant/brands), so Home
  Assistant shows a generic icon for the integration.

## Development

```bash
scripts/setup      # create .venv and install dependencies (uv sync)
scripts/develop    # run Home Assistant in debug mode with the integration loaded
scripts/lint       # ruff format --check, ruff check, mypy, pytest
```

Conventions live in [`CODE_STYLE.md`](./CODE_STYLE.md); architectural notes for
agents in [`CLAUDE.md`](./CLAUDE.md); contribution flow in
[`CONTRIBUTING.md`](./CONTRIBUTING.md).

## Credits

The Tuya BLE protocol implementation is derived from
[`PlusPlus-ua/ha_tuya_ble`](https://github.com/PlusPlus-ua/ha_tuya_ble) (MIT),
itself based on [`redphx/poc-tuya-ble-fingerbot`](https://github.com/redphx/poc-tuya-ble-fingerbot).

## License

[MIT](LICENSE)
