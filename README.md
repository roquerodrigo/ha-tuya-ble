# Tuya BLE

[![CI](https://github.com/roquerodrigo/ha-tuya-ble/actions/workflows/ci.yml/badge.svg)](https://github.com/roquerodrigo/ha-tuya-ble/actions/workflows/ci.yml)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

[![Sponsor](https://img.shields.io/badge/Sponsor-%E2%9D%A4-db61a2?logo=githubsponsors&logoColor=white&style=for-the-badge)](https://github.com/sponsors/roquerodrigo)

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

These sensors are battery powered and only listen for a moment after announcing
themselves, so a reading is taken right after the device announces itself
rather than at an arbitrary moment. Home Assistant suppresses an advertisement
identical to the one before it, and these sensors broadcast a constant one, so
the integration also re-checks every 30 seconds whether a reading is due.

Either way the decision is the same: the polling interval in the integration's
options is the *minimum* spacing between two readings (15 minutes by default),
never a guarantee of one. Each reading is one short connection — handshake, one
report, disconnect — and the device often has nothing new to say, in which case
the previous values are kept.

## Requirements

- A Bluetooth adapter or an [ESPHome Bluetooth proxy](https://esphome.io/components/bluetooth_proxy.html)
  in range of the device, with **active connections** enabled — values are read
  over a GATT connection, not from the advertisement.
- The device's `device_id` and `local_key`. Both come from the Tuya account
  that owns the device, and setup can read them from it for you — you sign in
  with the e-mail and password of the Tuya app, or enter the two values
  yourself. The `uuid` needed to pair is read from the advertisement, so it is
  never asked for.

## Installation

1. Add this repository to HACS as a custom repository (category *Integration*).
2. Install **Tuya BLE** and restart Home Assistant.
3. The device is discovered automatically once it advertises. Confirm the
   discovery and choose how to hand over the credentials:
   - **Use my Tuya account** — sign in with the e-mail, password, country code
     and region of the Tuya app account the device is bound to. The device id
     and the local key are read from the account, and the account credentials
     are used once and never stored.
   - **Enter the credentials myself** — type the `device_id` and the
     `local_key` as they appear in your Tuya account.

A device that is bound to a Tuya account broadcasts an obfuscated value in
place of its product id. The account knows which product it is; when the
credentials are typed in, setup asks. An unbound device names itself and the
question is skipped either way.

Re-authentication and reconfiguration offer the same choice, so a local key
that changed after re-pairing can be picked up from the account instead of
copied by hand.

## Development

```bash
scripts/setup      # create .venv and install dependencies (uv sync)
scripts/develop    # run Home Assistant in debug mode with the integration loaded
scripts/lint       # ruff format --check, ruff check, mypy, pytest
```

Conventions live in [`CODE_STYLE.md`](./CODE_STYLE.md); architectural notes for
agents in [`CLAUDE.md`](./CLAUDE.md); contribution flow in
[`CONTRIBUTING.md`](./CONTRIBUTING.md).

## Support

This integration is built and maintained on personal time, on hardware bought for the purpose. If it is useful to you, consider [sponsoring the work](https://github.com/sponsors/roquerodrigo) — it keeps the devices, the testing and the releases coming.

## Credits

The Tuya BLE protocol implementation is derived from
[`PlusPlus-ua/ha_tuya_ble`](https://github.com/PlusPlus-ua/ha_tuya_ble) (MIT),
itself based on [`redphx/poc-tuya-ble-fingerbot`](https://github.com/redphx/poc-tuya-ble-fingerbot).

## License

[MIT](LICENSE)
