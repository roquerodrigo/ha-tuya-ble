# Contributing

Bug reports, ideas and pull requests are welcome.

## Reporting a bug

Open an [issue](https://github.com/roquerodrigo/ha-tuya-ble/issues/new/choose)
with:

- the Home Assistant version, the integration version and the device model;
- whether the device is reached through the host's Bluetooth adapter or a
  Bluetooth proxy;
- what you did, what you expected and what happened;
- the diagnostics downloaded from the integration's menu (the device id, the
  local key and the device uuid are redacted) and the debug log.

## Development setup

The project uses [uv](https://docs.astral.sh/uv/) and Python 3.14.

```bash
scripts/setup      # install the dependencies into .venv
scripts/develop    # run Home Assistant at http://localhost:8123 with this integration loaded
```

`scripts/develop` uses the configuration in [`config/`](config/), which turns
on debug logging for the integration. The device has to be within reach of a
Bluetooth adapter or proxy that this Home Assistant instance can use.

The Bluetooth protocol and the Tuya account client live in
[tuya-ble-sdk](https://github.com/roquerodrigo/tuya-ble-sdk). Changes to the
protocol go there first. The integration pins the library version in
`custom_components/tuya_ble/manifest.json` and in `pyproject.toml`, and a test
checks that both pins match.

## Checks

Run these before opening a pull request. CI runs the same ones.

```bash
scripts/lint
```

It runs, in order:

```bash
uv run ruff format --check .                 # formatting
uv run ruff check .                          # lint
uv run mypy custom_components/tuya_ble       # type-check
uv run pytest                                # tests, coverage must stay at 90 % or more
```

`pre-commit install` runs ruff format, ruff check (with `--fix`) and mypy on
every commit, along with whitespace, end-of-file and JSON, YAML and TOML
checks.

Read [CODE_STYLE.md](CODE_STYLE.md) before adding or restructuring code.

## Adding a device

Supported devices are listed in `custom_components/tuya_ble/products.py`,
keyed by Tuya product id. The entities each product exposes are listed in
`SENSORS_BY_PRODUCT` in `custom_components/tuya_ble/sensor/__init__.py`, one
class per entity. A new device needs an entry in both, its name under
`device` and `selector.product` in the translations, and tests.

## Pull requests

1. Fork the repository and branch from `main`.
2. Write commit messages as [Conventional Commits](https://www.conventionalcommits.org/).
   Releases and their notes are generated from them. Mark breaking changes
   with `!` or a `BREAKING CHANGE:` footer.
3. Update `translations/en.json` and `translations/pt-BR.json` together when
   you change user-facing strings. A test fails when their keys differ.
4. Update the README when behaviour, configuration or entities change.
5. Fill in the pull request template.

## License

Contributions are released under the project's [MIT License](LICENSE).
