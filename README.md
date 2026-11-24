# Tuya BLE

<!-- ha-marketplace:exclude-start -->
[![CI](https://github.com/roquerodrigo/ha-tuya-ble/actions/workflows/ci.yml/badge.svg)](https://github.com/roquerodrigo/ha-tuya-ble/actions/workflows/ci.yml)
[![GitHub release](https://img.shields.io/github/v/release/roquerodrigo/ha-tuya-ble)](https://github.com/roquerodrigo/ha-tuya-ble/releases/latest)
[![Sponsor](https://img.shields.io/badge/Sponsor-%E2%9D%A4-db61a2?logo=githubsponsors&logoColor=white)](https://github.com/sponsors/roquerodrigo)

[![Open your Home Assistant instance and open a repository in the Marketplace.](https://my.home-assistant.io/badges/marketplace_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=roquerodrigo&repository=ha-tuya-ble&category=integration)
<!-- ha-marketplace:exclude-end -->

Follow the soil moisture, soil temperature and battery of a Tuya Bluetooth
soil sensor (SGS01) in Home Assistant. Home Assistant reads the sensor
directly over Bluetooth, through its own adapter or a Bluetooth proxy, so the
readings never go through the Tuya cloud. The Bluetooth protocol is
implemented in the companion library
[tuya-ble-sdk](https://github.com/roquerodrigo/tuya-ble-sdk).

## Features

- See the soil moisture and temperature of each plant, and use them to start
  watering or send a reminder.
- Know when the battery is getting low, as a percentage and as Low, Medium or
  High.
- Add a sensor as soon as Home Assistant spots it nearby, without typing its
  address.
- Read the device id and local key from your Tuya account during setup, so you
  do not have to copy them by hand.
- Keep the battery going: the sensor is read at most once per interval, which
  you choose.

## Requirements

- Home Assistant 2026.8.0 or newer.
- A Tuya SGS01 soil sensor.
- A Bluetooth adapter on the Home Assistant host, or an
  [ESPHome Bluetooth proxy](https://esphome.io/components/bluetooth_proxy.html),
  within range of the sensor and able to open connections. On an ESPHome
  proxy, this means active connections are turned on.
- The Tuya app account the sensor is paired with, or the device id and local
  key of the sensor.

<!-- ha-marketplace:exclude-start -->
## Installation

### Home Assistant Marketplace (recommended)

1. Select the **Open your Home Assistant instance** button above, or go to
   **Settings → Marketplace**, select **Add from link** in the upper right
   corner, enter `roquerodrigo/ha-tuya-ble` and select **Add**.
2. Select **Install**.
3. Restart Home Assistant.

The Marketplace comes with Home Assistant 2026.11 and later. On older
versions, add this repository to HACS as a custom repository of type
**Integration** and install it from there.

### Manual

1. Download `tuya_ble.zip` from the
   [latest release](https://github.com/roquerodrigo/ha-tuya-ble/releases/latest).
2. Extract it into `config/custom_components/tuya_ble/`.
3. Restart Home Assistant.
<!-- ha-marketplace:exclude-end -->

## Configuration

Home Assistant discovers the sensor when it announces itself over Bluetooth
and shows it under **Settings → Devices & services**. Select **Add** on the
discovered device. You can also go to
**Settings → Devices & services → Add integration**, search for **Tuya BLE**
and pick the sensor from the list of devices seen nearby.

The sensor only accepts a connection from someone who knows its device id and
local key. Choose how to provide them.

**Use my Tuya account** reads both values from the account the sensor is
paired with. The e-mail and password are used once for this and are not
stored.

| Field        | What to enter                                                              | Default       |
|--------------|----------------------------------------------------------------------------|---------------|
| E-mail       | The e-mail of your Tuya app account                                        |               |
| Password     | The password of that account                                               |               |
| Country code | The calling code the account was registered with, for example `1` or `55`  |               |
| Region       | Where the account is hosted: United States, Europe, Western Europe, China or India | United States |

**Enter the credentials myself** asks for the values as they appear for the
sensor in your Tuya account.

| Field     | What to enter                                   |
|-----------|-------------------------------------------------|
| Device id | The device id of the sensor                     |
| Local key | The local key of the sensor, at least 6 characters |
| Product   | Soil sensor (SGS01). Asked only when the sensor does not announce what it is, which is the case once it is paired with a Tuya account |

The credentials are not tested during setup, because the sensor sleeps most of
the time. The first reading arrives the next time the sensor announces itself,
which can take several minutes. Until then the entities show as unknown. If
the local key is wrong, Home Assistant asks you to re-authenticate at that
point.

The device is named **Soil sensor** and the entry gets the model followed by
the last six characters of the Bluetooth address, for example `SGS01 A1B2C3`.

To change the credentials later, open the integration and select
**Reconfigure**. Re-pairing the sensor in the Tuya app gives it a new local
key. When that happens Home Assistant asks you to re-authenticate, with the
same two choices as the first setup.

## Options

Open the integration and select **Configure**.

| Setting                                      | Default | Range                       | Effect |
|----------------------------------------------|---------|-----------------------------|--------|
| Minimum interval between readings (seconds) | 900     | 60 or more, in steps of 10  | The sensor is read at most once per interval, the next time it announces itself |

A longer interval saves battery. Soil moisture changes slowly, so the default
of 15 minutes is enough for most plants. An interval longer than one hour is
treated as one hour.

## Entities

Each sensor becomes one device with these entities.

| Entity        | Type   | Unit or states      | Notes      |
|---------------|--------|---------------------|------------|
| Soil moisture | Sensor | %                   |            |
| Temperature   | Sensor | °C, one decimal     |            |
| Battery       | Sensor | %                   | Diagnostic |
| Battery state | Sensor | Low, Medium or High | Diagnostic |

## How it works

The sensor runs on a battery and sleeps between short announcements over
Bluetooth. Home Assistant checks every 30 seconds whether a reading is due.
When the interval has passed and the sensor is within reach, it connects,
asks for the current values and disconnects.

The sensor often has nothing new to report. In that case the entities keep
their last values. If a reading fails, the wait before the next attempt
doubles after each failure, up to one hour, and returns to your interval
after the next successful reading. This keeps a sensor that is out of range
from occupying a Bluetooth proxy that other devices also use.

Readings are always local. The Tuya cloud is contacted only during setup,
re-authentication or reconfiguration, and only if you choose
**Use my Tuya account**.

## Troubleshooting

**No supported Tuya BLE device was found nearby.** The sensor has not been
heard yet. Make sure it is within range of a Bluetooth adapter or proxy that
can open connections, wait a few minutes for it to announce itself and try
again.

**The entities stay unknown after setup.** The first reading happens the next
time the sensor announces itself and the adapter or proxy can connect to it.
Check that the proxy has active connections turned on and is close enough to
the sensor.

**The Tuya account turned the sign-in away.** The account refuses sign-ins
after a few attempts in a row. Wait a minute and try again.

**This account does not list the device seen at this address.** The account
you signed in to is not the one the sensor is paired with. Sign in with the
right account, or enter the credentials yourself.

**Home Assistant asks me to re-authenticate.** The sensor rejected the stored
local key, or ignored the handshake of three readings in a row, which is
what it does with a wrong key. This usually means it was re-paired in the
Tuya app. Choose **Use my Tuya account** to read the new key.

**Something else is wrong.** Enable debug logging from the integration's
menu, reproduce the problem, then download the diagnostics and attach both to
an [issue](https://github.com/roquerodrigo/ha-tuya-ble/issues). The device id,
the local key and the device uuid are removed from the diagnostics.

## Known limitations

- The SGS01 soil sensor is the only supported device.
- Values are read on a schedule, not pushed. A change shows up at the next
  reading, up to one interval later.
- The sensor accepts one connection at a time. While the Tuya app is
  connected to it, Home Assistant cannot read it.

## Support

This integration is built and maintained on personal time, on hardware bought
for the purpose. If it is useful to you, consider
[sponsoring the work](https://github.com/sponsors/roquerodrigo). It keeps the
devices, the testing and the releases coming.

Report bugs and request features in the
[issue tracker](https://github.com/roquerodrigo/ha-tuya-ble/issues).

<!-- ha-marketplace:exclude-start -->
## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the development setup and
workflow, and [CODE_STYLE.md](CODE_STYLE.md) for the code conventions.

## Credits

The Tuya BLE protocol implementation is derived from
[PlusPlus-ua/ha_tuya_ble](https://github.com/PlusPlus-ua/ha_tuya_ble) (MIT),
itself based on
[redphx/poc-tuya-ble-fingerbot](https://github.com/redphx/poc-tuya-ble-fingerbot).

## License

[MIT](LICENSE)
<!-- ha-marketplace:exclude-end -->
