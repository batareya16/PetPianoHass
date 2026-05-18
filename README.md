# Pet Piano — Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![HA Version](https://img.shields.io/badge/Home%20Assistant-2023.6%2B-blue.svg)](https://www.home-assistant.io/)

A Home Assistant custom integration for the **Pet Piano** — a smart BLE pet feeder that teaches your cat to play piano keys in exchange for treats. This integration was built by reverse-engineering the official Android app's Bluetooth protocol.

---

## What is Pet Piano?

Pet Piano is a device that sits in front of your cat. It plays melodies and rewards your cat with food when they press the correct piano keys. You can set up a feeding schedule, control portion sizes, adjust difficulty, and monitor the device — all from Home Assistant.

---

## Features

| Entity | Type | Description |
|---|---|---|
| Battery | Sensor | Battery level in % |
| Food Level | Sensor | Hopper fill level (0–7) |
| Portions Today | Sensor | How many portions have been dispensed today |
| Mode | Sensor | Current operating mode (Normal / Tutor / Concert) |
| Device Time | Sensor | Internal RTC clock of the device |
| Meal 1 / 2 / 3 Time | Sensor | Scheduled feeding times |
| Motor Jam | Binary Sensor | True if the dispenser motor is stuck |
| Wall Power | Binary Sensor | True if running on AC adapter |
| Schedule Active | Binary Sensor | True if the feeding schedule is enabled |
| Meal 1 / 2 / 3 Active | Binary Sensor | True if each meal slot is enabled |
| Schedule | Switch | Enable or disable the feeding schedule |
| Volume | Number | Speaker volume (0–7) |
| Tutor Level | Number | Difficulty — how many keys the cat must press to get food (0–7) |
| Dispense Now | Button | Immediately dispense one portion |

### Modes explained

- **Normal** — the piano plays and dispenses food when the cat presses the correct keys
- **Tutor** — the device guides the cat step by step, increasing difficulty as the Tutor Level goes up
- **Concert** — 30-minute pure play sessions; food is only dispensed on schedule, not during play

---

## Requirements

- Home Assistant 2023.6.0 or newer
- A Bluetooth adapter accessible to your HA instance (built-in or USB dongle)
- Pet Piano device powered on and within Bluetooth range (~10 m)

---

## Installation

### Via HACS (recommended)

1. Open **HACS** in your Home Assistant sidebar
2. Go to **Integrations**
3. Click the **⋮** menu in the top right → **Custom repositories**
4. Enter this repository URL, select category **Integration**, click **Add**
5. Find **Pet Piano** in the list and click **Download**
6. Restart Home Assistant

### Manual

1. Download or clone this repository
2. Copy the `custom_components/pet_piano/` folder into your HA config directory:
   ```
   /config/custom_components/pet_piano/
   ```
3. Restart Home Assistant

---

## Setup

1. Make sure your Pet Piano is **turned on** and within Bluetooth range
2. Go to **Settings → Devices & Services → Add Integration**
3. Search for **Pet Piano**
4. If the device is discovered automatically, confirm it — otherwise select it from the list
5. Done! Entities will appear under the **Pet Piano** device

---

## Lovelace Card (optional)

A custom dashboard card is included that shows all important info at a glance with a dispense button and schedule overview.

**Step 1** — copy `www/pet-piano-card.js` to `/config/www/`

**Step 2** — register it as a Lovelace resource:
Settings → Dashboards → ⋮ → Resources → Add resource:
```
URL:  /local/pet-piano-card.js
Type: JavaScript module
```

**Step 3** — add the card to your dashboard via Edit → Add Card → Manual:
```yaml
type: custom:pet-piano-card
entity_prefix: pet_piano
```

---

## How it works

The Pet Piano exposes a custom BLE GATT service with 4 characteristics. Each characteristic holds a 32-bit value packed with multiple bit-fields. The integration reads all four on every poll and writes back only when you change something.

| Characteristic | UUID | Contents |
|---|---|---|
| Settings 1 | `34333333-2222-2222-1111-111100000000` | Mode, battery, portions, motor status |
| Settings 2 | `35333333-2222-2222-1111-111100000000` | Volume, meal sizes, max portions |
| RTC Clock | `36333333-2222-2222-1111-111100000000` | Device time, food level sensor |
| Schedule | `37333333-2222-2222-1111-111100000000` | Three meal times with AM/PM and active flags |

The integration polls every 60 seconds. On failed connections it retries up to 3 times with backoff, and keeps showing the last known values rather than marking the device unavailable.

---

## Troubleshooting

**Device not found during setup**
Make sure the Piano is turned on. The HA Bluetooth scanner needs to see an advertisement from the device before it shows up in the integration list. Try moving the Piano closer to the HA host and waiting 30 seconds.

**Sensors show strange values after first install**
The bit-field decoding is based on reverse engineering and may need minor calibration for your specific device firmware. Enable the hidden **Raw CHAR1 / CHAR2 / CHAR3 / CHAR4** diagnostic sensors (Settings → Devices → Pet Piano → entities) and share the hex values in a GitHub issue — we can update the decoding together.

**Frequent disconnections**
The Pet Piano is designed for short BLE sessions (connect → read/write → disconnect). The integration respects this pattern. If disconnections still occur, try increasing the poll interval in `coordinator.py` (`SCAN_INTERVAL`).

**Motor Jam alert**
Clear any blockage in the food dispenser and power-cycle the device. The flag resets automatically after the next successful dispense.

---

## Contributing

Pull requests are welcome. If you have a different firmware version and your Raw CHAR values don't decode correctly, please open an issue with the hex bytes and what the correct values should be — it helps improve the bit-field map for everyone.

---

## License

MIT
