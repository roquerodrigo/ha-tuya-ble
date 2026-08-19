# CLAUDE.md

Guidance for Claude Code (claude.ai/code) agents working in this repository.

## Always read `CODE_STYLE.md` first

Before creating, renaming or restructuring any file/class/function, **read [`CODE_STYLE.md`](./CODE_STYLE.md)**. It is the single source of truth for conventions: language, file organisation, naming, typing, properties vs `__init__`, imports, docstrings, comments, coordinator pattern, diagnostics layout, translations, lint workflow.

For user-facing topics (supported devices, installation, useful commands), see [`README.md`](./README.md).

This file deliberately avoids restating those rules — it only adds:

1. The verification workflow agents must run after every change.
2. The architectural reasoning that is not obvious from `CODE_STYLE.md` alone.
3. Where the repository currently stands against the design in [`PLAN.md`](./PLAN.md).

## Current state

The design in [`PLAN.md`](./PLAN.md) is implemented: the blueprint's sample
cloud integration is gone and `custom_components/tuya_ble/` reads a Tuya BLE
device over Bluetooth. The protocol lives in the companion SDK
`tuya-ble-sdk` (sibling repository), which this integration pins exactly from
`manifest.json`.

`PLAN.md` remains the reference for *why* the design looks the way it does; the
architecture section below records *what* exists.

## Verification workflow

**After every code change, always run lint then tests, in that order, before declaring the task done. Either run `scripts/lint` (a thin wrapper that only chains the four commands) or run them directly:**

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy custom_components/tuya_ble
uv run pytest
```

- Lint runs `ruff format`, `ruff check` and `mypy` — all configured in `pyproject.toml`. Fix any failure and re-run before moving on.
- `pytest` enforces a **90 % coverage gate** (`--cov-fail-under` in `pyproject.toml`).

Both gates mirror CI (`.github/workflows/ci.yml`). Skip this only when the change literally cannot affect lint or tests (e.g., README-only edits).

## Bumping the Home Assistant version

The Home Assistant version is pinned in two places and **must be updated together**, otherwise CI, HACS and the test harness drift apart:

1. `pyproject.toml` `[dependency-groups] dev` — `homeassistant==<X.Y.Z>` (runtime/CI lint + mypy) **and** `pytest-homeassistant-custom-component==<matching release>` (the test harness ships its own pinned `homeassistant`; the two pins must come from the same HA release, otherwise lint and tests resolve different cores).
2. `hacs.json` — `"homeassistant": "<X.Y.Z>"` (minimum HA core enforced by HACS).

Verify the pairing on PyPI before committing: the `requires_dist` of `pytest-homeassistant-custom-component` must list the same `homeassistant==<X.Y.Z>` you pinned in `pyproject.toml`.

## Architecture

One config entry is one physical device, driven by Bluetooth advertisements:

```
config_flow.py   → reads the advertisement, asks for device_id + local_key
__init__.py      → builds the coordinator and forwards the sensor platform
coordinator.py   → polls when a reading is due; returns the datapoints
sensor.py        → one class per entity, picked from a per-product table
```

### Why the coordinator is not a `DataUpdateCoordinator`

The supported devices are battery powered and only listen for a moment after
they advertise, so `coordinator.py` uses `ActiveBluetoothDataUpdateCoordinator`:
Home Assistant calls `needs_poll_method` on every advertisement, and
`scan_interval` (options flow, default 900 s) becomes the minimum spacing
between two readings rather than a schedule. The coordinator holds no client —
`TuyaBleClient` is built per poll, connects, reads one report and disconnects.

**Advertisements alone are not enough**, and this is the non-obvious part.
Home Assistant returns early from an advertisement whose payload is
byte-identical to the previous one (`habluetooth.manager`), and these sensors
broadcast a constant payload — so the callback fires once, when the entry
loads, and never again. Measured against real hardware, the device was read
only after a reload, whatever `scan_interval` said. `async_poll_if_due`, wired
to a `POLL_CHECK_INTERVAL_SECONDS` timer in `async_setup_entry`, therefore
re-offers the last advertisement to the same `_needs_poll`, which stays the
single decision point. The timer ticks faster than the interval so a reading is
not delayed a whole extra cycle by the tick grid.

A reading that returns no datapoint is normal — the device acknowledges the
request and stays quiet unless it has something to report — so the coordinator
keeps the previous values instead of surfacing an error.

A `TuyaBleAuthenticationError` from the SDK means the stored local key was
rejected; the coordinator starts the reauth flow and re-raises.

### Entry typing

The `data/` package holds one TypedDict/dataclass per file. `data/__init__.py`
defines the `type` aliases — `TuyaBleConfigEntry = ConfigEntry[TuyaBleData]`,
`TuyaBleDataPoints = Mapping[int, DataPoint]`, `JsonPrimitive`/`JsonValue`/
`JsonObject` — and re-exports every symbol. `TuyaBleData(coordinator, product,
integration)` lives in `data/runtime.py`. State lives on `entry.runtime_data`,
never on `hass.data`.

`data/config_data.py` is what one entry stores: `address` and `product_id` come
from the advertisement, `uuid` is decrypted from it, and `device_id` /
`local_key` come from the user's Tuya account.

### Config flow surface

- `async_step_bluetooth` — discovery; parses the advertisement, aborts with
  `not_supported` when the uuid cannot be read, and sets the unique id from the
  formatted MAC.
- `async_step_bluetooth_confirm` — asks for `device_id` and `local_key`, plus
  the product when the advertisement did not name it.
- `async_step_user` — lists the supported devices seen nearby.
- `async_step_reauth` / `async_step_reauth_confirm` and
  `async_step_reconfigure` — both re-ask for the credentials through one
  `_async_update_credentials` helper.

The credentials are **not** tried against the device while the flow is open: it
is asleep most of the time, so a connection attempt would time out far more
often than it would catch a typo. `_validate` only rejects what cannot possibly
work; a wrong local key surfaces on the first poll as a reauth prompt.

### Products

`products.py` is the catalogue of supported devices, keyed by product id.
`sensor.py` maps the same key to the entity classes that product exposes, so a
second device is a table entry rather than a new platform.

The product id is **not** reliably readable from the air: a device bound to a
Tuya account broadcasts an obfuscated value in its place (those bytes still
decrypt the uuid — they are the key material — but they name no product).
Discovery therefore only requires the uuid, and the product is asked for
whenever the advertisement did not name it.

### Diagnostics

`diagnostics.py` returns `TuyaBleDiagnosticsPayload`. `device_id`, `local_key`
and `uuid` are redacted via `async_redact_data` (driven by
`TO_REDACT: frozenset[str]`); the dump also carries a summary of the last
advertisement and the last datapoint report.
