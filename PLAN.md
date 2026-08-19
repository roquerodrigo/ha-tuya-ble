# Implementation plan

Goal: read a **Tuya SGS01 soil sensor** in Home Assistant over Bluetooth, with no
Tuya cloud dependency at runtime.

Work happens in two repositories:

| Repository | Role |
| --- | --- |
| `tuya-ble-sdk` (sibling directory) | the Tuya BLE protocol, published to PyPI |
| `ha-tuya-ble` (this one) | the Home Assistant integration consuming it |

Both were scaffolded from `ha-integration-blueprint` and still carry the
blueprint's **sample** code (an aiohttp client, a username/password config flow,
a demo sensor). Replacing it is the first task, not a leftover.

---

## The device

Confirmed live before this plan was written — the sensor advertises and is
reachable:

```
address           <the sensor's MAC>
name              TY
rssi              -67           (via an ESPHome Bluetooth proxy, connectable)
service_uuids     0000a201-0000-1000-8000-00805f9b34fb
service_data      00 6776796767336d38          -> type 0, product_id "gvygg3m8"
manufacturer_data 0x07D0: 00 03 0000 0100 <16 bytes, encrypted uuid>
                          ^     ^         ^ encrypted uuid (16 bytes)
                          |     protocol version 3
                          bit 0x80 = bound flag
```

Decrypting `manufacturer_data[6:]` with `AES-128-CBC`, key **and** IV both
`md5(product_id)`, yields the device `uuid` in ASCII — verified against the
value the Tuya account reports for this device. So the config flow only has to
ask for `device_id` and `local_key`.

Datapoints (from the product schema):

| DP | Code | Type | Meaning |
| --- | --- | --- | --- |
| 3 | `humidity` | value | soil moisture, % |
| 5 | `temp_current` | value | temperature, ÷10, °C |
| 9 | `temp_unit_convert` | enum `c`/`f` | display unit on the device |
| 14 | `battery_state` | enum `low`/`middle`/`high` | battery state |
| 15 | `battery_percentage` | value | battery, % |

The device is battery powered and **sleeps between advertisements**: it is not
reachable at an arbitrary moment, only shortly after it advertises.

## The protocol

Reference implementation: [`PlusPlus-ua/ha_tuya_ble`](https://github.com/PlusPlus-ua/ha_tuya_ble)
(MIT), file `custom_components/tuya_ble/tuya_ble/tuya_ble.py`. Port it — do not
vendor it — and keep the credit in both READMEs.

```
GATT service     0000a201-0000-1000-8000-00805f9b34fb
notify           00002b10-0000-1000-8000-00805f9b34fb
write            00002b11-0000-1000-8000-00805f9b34fb
MTU              20 bytes -> every packet is fragmented and reassembled
login_key        md5(local_key[:6])
session_key      md5(local_key[:6] + srand)      srand from the DEVICE_INFO reply
cipher           AES-128-CBC, random IV per packet, CRC16 over the frame
```

Handshake: `FUN_SENDER_DEVICE_INFO (0x0000)` encrypted with the *login key*
returns `srand`, protocol version, bound flag and auth key → derive the session
key → `FUN_SENDER_PAIR (0x0001)` with `uuid + local_key[:6] + device_id`, padded
to 44 bytes (reply `0` = paired, `2` = already paired) → `FUN_SENDER_DEVICE_STATUS
(0x0003)` asks the device to report every datapoint, which arrives as
`FUN_RECEIVE_DP (0x8001)` / `FUN_RECEIVE_TIME_DP (0x8003)` notifications. The
device may also ask for the current time (`0x8011`/`0x8012`) and expects a
response.

Datapoint payload: `dp_id (1) | type (1) | length (1) | value` where type is
`0 raw, 1 bool, 2 value (int32 BE), 3 string, 4 enum, 5 bitmap`.

---

## Phase 1 — `tuya-ble-sdk`

Mirror the layout of the existing `ttlock-ble` SDK (the other BLE package in the
fleet), one top-level class per file:

```
src/tuya_ble_sdk/
├── client.py               # connect, handshake, read datapoints, disconnect
├── crypto.py               # AES-128-CBC helpers, login/session key, CRC16,
│                           # advertisement uuid decryption
├── protocol/
│   ├── constants.py        # UUIDs, command codes, datapoint types, MTU
│   ├── frame.py            # build/parse one packet (seq num, code, CRC)
│   └── reassembler.py      # join fragmented notifications
├── commands/               # device info, pair, status, time replies
├── models/                 # TuyaBleCredentials, DataPoint, DeviceInfo,
│                           # AdvertisementInfo
└── exceptions/             # rename the scaffold's three errors as needed
```

- Replace the sample `client.py` (and `tests/test_client.py`) — the current one
  is an aiohttp demo. Swap `aiohttp` for `bleak`, `bleak-retry-connector` and
  `cryptography` in `pyproject.toml` at the same time. Use `cryptography`, not
  `pycryptodome`: Home Assistant already ships it, and `ttlock-ble` set that
  precedent.
- The client takes an already-resolved `BLEDevice` (Home Assistant owns
  discovery) plus `TuyaBleCredentials`, and exposes something as small as
  `async_read_datapoints() -> dict[int, DataPoint]`, connecting and disconnecting
  around the read. **No permanent connection**: the device is battery powered and
  a proxy has few connection slots.
- `parse_advertisement(service_data, manufacturer_data)` belongs here too — it is
  protocol, and the config flow needs `product_id` and `uuid` from it.
- Ship a `typer` CLI (`tuya-ble`) that dumps datapoints from
  `--address/--device-id/--local-key`, like `ttlock-ble` does. It is what proves
  the protocol against the real sensor before any Home Assistant code exists.
- Tests are network-free: exercise frame building/parsing, crypto and the
  handshake against recorded byte fixtures with a fake transport. Keep the 90 %
  gate.

## Phase 2 — `ha-tuya-ble`

The scaffold already settles the Bluetooth plumbing around the code: the manifest
carries the matcher and the `bluetooth_adapters` dependency, the dev dependency
group carries the packages `bluetooth`/`usb` need to start under test
(`aiousbwatcher`, `bleak`, `bluetooth-adapters`, `dbus-fast`, `habluetooth`,
`serialx`), and `tests/conftest.py` overrides `enable_custom_integrations` to
bring the stack up — without that override every test fails on an integration
that never loaded. Home Assistant is pinned to `2026.8.0` in `pyproject.toml` and
`hacs.json` together.


- `manifest.json` already declares the Bluetooth matcher
  (`service_data_uuid 0000a201…`, `connectable: true`) and
  `dependencies: ["bluetooth_adapters"]`. Add `requirements:
  ["tuya-ble-sdk==<version>"]` once the SDK is released — the integration pins the
  SDK exactly, while the SDK never pins its own runtime dependencies.
- **Config flow**: `async_step_bluetooth` (discovery; parse the advertisement for
  `product_id`/`uuid`, abort if the product is not in the catalogue) →
  `async_step_bluetooth_confirm` asking for `device_id` and `local_key`, plus an
  `async_step_user` path that picks from `async_discovered_service_info`. Unique
  id is the formatted MAC. A rejected `local_key` raises `ConfigEntryAuthFailed`
  and drives the reauth step the scaffold already has. Drop the
  username/password steps.
- **Coordinator**: `ActiveBluetoothDataUpdateCoordinator` — Home Assistant polls
  when an advertisement arrives and `needs_poll_method` says the last successful
  read is older than the interval. That is what matches a sleeping device;
  a plain `DataUpdateCoordinator` on a timer would mostly hit a device that is
  not listening. Keep the options flow's `scan_interval` as the minimum spacing
  between reads (default 15 min is plenty for soil moisture, and it is a AAA
  battery).
- **Entities** — a `sensor.py` catalogue keyed by `(category, product_id)`, so a
  second Tuya BLE device is a table entry, not a new platform:

  | Entity | DP | Device class | Unit | Category |
  | --- | --- | --- | --- | --- |
  | soil moisture | 3 | `moisture` | `%` | — |
  | temperature | 5 (÷10) | `temperature` | `°C` | — |
  | battery | 15 | `battery` | `%` | diagnostic |
  | battery state | 14 | `enum` | — | diagnostic |

  Device info: `connections={(CONNECTION_BLUETOOTH, address)}`, model `SGS01`,
  manufacturer `Tuya`.
- Delete what does not apply (`api.py`, `repairs.py` and their tests) rather than
  leaving a sample around; update `translations/en.json` + `pt-BR.json` (parity is
  enforced), `icons.json`, `diagnostics.py` (redact `local_key`, include the last
  advertisement via `async_last_service_info`) and `CLAUDE.md`'s architecture
  section.
- Replace the placeholder artwork in `custom_components/tuya_ble/brand/`, which
  is where the assets are served from.
- Add a packaging test asserting the SDK pin in `manifest.json` matches the pin in
  the dev dependency group, as `ha-ttlock-ble` does.

## Phase 3 — run it for real

Order matters; each step is evidence for the next.

1. `uv build` the SDK, install the wheel into the Home Assistant container and
   run the CLI/SDK against the sensor. A change's first real execution is never a
   published version.
2. Mirror `custom_components/tuya_ble/` into
   `~/smart-home/apps/home-assistant/config/custom_components/tuya_ble/` and
   **restart** the container — reloading a config entry does not re-import Python
   modules.
3. Add the device from the discovery card, then prove it: entity states, and Home
   Assistant logs showing the handshake and the datapoint report.
4. Only then open the pull requests (SDK first, then the integration bump).
   Merging and releasing are the maintainer's call.

## Watch out for

- **The advertisement's bound flag read `0`** on this sensor when the plan was
  written (unbound), while the Tuya account still listed it. If `PAIR` is
  rejected, the stored `local_key` is stale — re-pair the device in the Tuya app
  and read the key again.
- **Resolved during phase 3.** After re-pairing, the device advertises with the
  bound flag set *and* an obfuscated value in the product-id record: those bytes
  are no longer the printable `gvygg3m8`, though `md5()` of them still decrypts
  the uuid. So the product id cannot be read from the air on a bound device, and
  the config flow asks for it instead. Hash the record as broadcast — decoding
  it as text first rejects every bound device.
- **Protocol version 3** — the reference implementation branches on it in a few
  places (`DPS_V4` codes exist for v4 devices). Test against what the device
  actually answers, not against the branch that looked most complete.
- **Only one connection at a time.** The Tuya app on a phone holds the device
  while it is open; a failing connection during development is often that.
- Both repositories are public: no local keys, device ids or MACs in the code,
  the tests or the commit messages.
