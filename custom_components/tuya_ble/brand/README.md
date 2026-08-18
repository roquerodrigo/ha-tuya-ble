# Brand assets

Tuya's own icon and wordmark — the brand of the devices this integration
speaks to. They are the same artwork
[home-assistant/brands](https://github.com/home-assistant/brands) carries for
Tuya's other integrations.

| File          | Shape                   | Size      |
| ------------- | ----------------------- | --------- |
| `icon.png`    | square symbol           | 256×256   |
| `icon@2x.png` | square symbol           | 512×512   |
| `icon.svg`    | square vector of `icon` | square    |
| `logo.png`    | landscape wordmark      | 512×256   |
| `logo@2x.png` | landscape wordmark      | 1024×512  |

**Still to do:** submit these files to
[home-assistant/brands](https://github.com/home-assistant/brands) under the
`tuya_ble` domain. Until that lands, Home Assistant renders a generic icon for
the integration no matter what this directory holds — the files here are only
the source for that submission.
