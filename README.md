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

> **Status: scaffold.** The repository is set up and the design is settled, but
> the device support is not implemented yet. See [`PLAN.md`](./PLAN.md).

## Supported devices

| Category | Product ID | Device | Entities |
| --- | --- | --- | --- |
| `zwjcy` | `gvygg3m8` | Soil sensor (SGS01) | soil moisture, temperature, battery level, battery state |

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
