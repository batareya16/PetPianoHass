"""Pet Piano BLE Coordinator — handles all BLE communication."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from bleak import BleakClient, BleakError
from bleak.backends.device import BLEDevice

from homeassistant.components.bluetooth import async_ble_device_from_address
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    CHAR1_SETTINGS_UUID, CHAR4_SETTINGS2_UUID,
    CHAR2_RTC_UUID, CHAR3_SCHEDULE_UUID,
    bytes_to_int, int_to_bytes, get_field, set_field,
    CHAR1_MODE, CHAR1_MODE_TUTOR, CHAR1_PORTIONS_TODAY, CHAR1_BATTERY,
    CHAR1_POWER_SOURCE, CHAR1_TUTOR_LEVEL,
    CHAR1_MOTOR_JAM, CHAR1_MANUAL_DISPENSE,
    CHAR4_VOLUME, CHAR4_MAX_PORTIONS, CHAR4_MEAL_SIZE_1,
    CHAR4_MEAL_SIZE_2, CHAR4_SCHEDULE_ENABLE,
    CHAR4_MELODY_ASSIST,
    CHAR2_SECONDS, CHAR2_MINUTE, CHAR2_HOUR,
    CHAR2_AMPM, CHAR2_DAY, CHAR2_MONTH, CHAR2_FOOD_LEVEL,
    CHAR3_MEAL1_MINUTE, CHAR3_MEAL1_HOUR, CHAR3_MEAL1_AMPM, CHAR3_MEAL1_ACTIVE,
    CHAR3_MEAL2_MINUTE, CHAR3_MEAL2_HOUR, CHAR3_MEAL2_AMPM, CHAR3_MEAL2_ACTIVE,
    CHAR3_MEAL3_MINUTE, CHAR3_MEAL3_HOUR, CHAR3_MEAL3_AMPM, CHAR3_MEAL3_ACTIVE,
    QUARTER_HOUR_MAP, MODE_MAP,
)

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=60)   # poll every 60 s — less hammering


class PetPianoData:
    """Holds all decoded data from the device."""

    def __init__(self) -> None:
        # Raw bytes for debugging
        self.raw: dict[str, str] = {}

        # CHAR1
        self.mode: int = 0
        self.portions_today: int = 0
        self.battery: int = 0
        self.power_source: bool = False   # True = wall adapter
        self.double_note: bool = False
        self.motor_jam: bool = False

        # CHAR4
        self.volume: int = 3
        self.max_portions: int = 0
        self.meal_size_1: int = 0
        self.meal_size_2: int = 0
        self.schedule_enabled: bool = False
        self.melody_assist: bool = False

        # CHAR2
        self.rtc_hour: int = 0
        self.rtc_minute: int = 0
        self.rtc_second: int = 0
        self.rtc_ampm: int = 0        # 0=AM, 1=PM
        self.rtc_day: int = 1
        self.rtc_month: int = 1
        self.food_level: int = 0      # 0-7: hopper fill level (read-only sensor)
        self.tutor_level: int = 0     # 0-7: difficulty / keys required (writable)

        # CHAR3 — meal schedule
        self.meal1_hour: int = 8
        self.meal1_minute: int = 0
        self.meal1_ampm: int = 0
        self.meal1_active: bool = False   # True = pending (not yet dispensed today)

        self.meal2_hour: int = 12
        self.meal2_minute: int = 0
        self.meal2_ampm: int = 1
        self.meal2_active: bool = False

        self.meal3_hour: int = 6
        self.meal3_minute: int = 0
        self.meal3_ampm: int = 1
        self.meal3_active: bool = False


def _decode_char1(data: bytes) -> dict:
    v = bytes_to_int(data)
    _LOGGER.debug("CHAR1 raw=%s int=0x%08X", data.hex(), v)
    raw_battery = get_field(v, *CHAR1_BATTERY)  # 0-63, scale to 0-100%
    battery_pct = round(raw_battery * 100 / 63)
    # Mode logic from APK:
    # - Tutor:   g$CurrentLevel (bits 24-26) > 0
    # - Concert: g$Mode (bits 0-1) = 1
    # - Normal:  everything else
    level = get_field(v, *CHAR1_TUTOR_LEVEL)
    concert = get_field(v, *CHAR1_MODE)
    if level > 0:
        mode = 1        # Tutor
    elif concert == 1:
        mode = 2        # Concert
    else:
        mode = 0        # Normal
    return {
        "mode":          mode,
        "portions_today":get_field(v, *CHAR1_PORTIONS_TODAY),
        "battery":       battery_pct,
        "power_source":  bool(get_field(v, *CHAR1_POWER_SOURCE)),  # 1=wall
        "tutor_level":   get_field(v, *CHAR1_TUTOR_LEVEL),
        "motor_jam":     bool(get_field(v, *CHAR1_MOTOR_JAM)),
    }


def _decode_char4(data: bytes) -> dict:
    v = bytes_to_int(data)
    _LOGGER.debug("CHAR4 raw=%s int=0x%08X", data.hex(), v)
    return {
        "volume":           get_field(v, *CHAR4_VOLUME),
        "max_portions":     get_field(v, *CHAR4_MAX_PORTIONS),
        "meal_size_1":      get_field(v, *CHAR4_MEAL_SIZE_1),
        "meal_size_2":      get_field(v, *CHAR4_MEAL_SIZE_2),
        "schedule_enabled": bool(get_field(v, *CHAR4_SCHEDULE_ENABLE)),
        "melody_assist":    bool(get_field(v, *CHAR4_MELODY_ASSIST)),
    }


def _decode_char2(data: bytes) -> dict:
    v = bytes_to_int(data)
    _LOGGER.debug("CHAR2 raw=%s int=0x%08X", data.hex(), v)
    return {
        "rtc_second": get_field(v, *CHAR2_SECONDS),
        "rtc_minute": get_field(v, *CHAR2_MINUTE),
        "rtc_hour":   get_field(v, *CHAR2_HOUR),
        "rtc_ampm":   get_field(v, *CHAR2_AMPM),
        "rtc_day":    get_field(v, *CHAR2_DAY),
        "rtc_month":  get_field(v, *CHAR2_MONTH),
        "food_level": get_field(v, *CHAR2_FOOD_LEVEL),
    }


def _decode_char3(data: bytes) -> dict:
    v = bytes_to_int(data)
    _LOGGER.debug("CHAR3 raw=%s int=0x%08X", data.hex(), v)
    # g$MealtStatus: 1 = meal slot is configured/enabled
    # We expose as True = slot is configured
    return {
        "meal1_minute":  QUARTER_HOUR_MAP.get(get_field(v, *CHAR3_MEAL1_MINUTE), 0),
        "meal1_hour":    get_field(v, *CHAR3_MEAL1_HOUR),
        "meal1_ampm":    get_field(v, *CHAR3_MEAL1_AMPM),
        "meal1_pending": bool(get_field(v, *CHAR3_MEAL1_ACTIVE)),  # 1=slot configured
        "meal2_minute":  QUARTER_HOUR_MAP.get(get_field(v, *CHAR3_MEAL2_MINUTE), 0),
        "meal2_hour":    get_field(v, *CHAR3_MEAL2_HOUR),
        "meal2_ampm":    get_field(v, *CHAR3_MEAL2_AMPM),
        "meal2_pending": bool(get_field(v, *CHAR3_MEAL2_ACTIVE)),
        "meal3_minute":  QUARTER_HOUR_MAP.get(get_field(v, *CHAR3_MEAL3_MINUTE), 0),
        "meal3_hour":    get_field(v, *CHAR3_MEAL3_HOUR),
        "meal3_ampm":    get_field(v, *CHAR3_MEAL3_AMPM),
        "meal3_pending": bool(get_field(v, *CHAR3_MEAL3_ACTIVE)),
    }


class PetPianoCoordinator(DataUpdateCoordinator[PetPianoData]):
    """Coordinator that polls Pet Piano over BLE."""

    def __init__(self, hass: HomeAssistant, address: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.address = address
        self._lock = asyncio.Lock()   # prevent concurrent BLE sessions

    # ── internal BLE helpers ────────────────────────────────────────────────

    def _make_client(self) -> BleakClient:
        ble_device: BLEDevice | None = async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )
        if ble_device is None:
            raise UpdateFailed(f"PetPiano ({self.address}) not in BLE scanner cache")
        return BleakClient(ble_device, timeout=20.0)

    async def _read_char(self, client: BleakClient, uuid: str) -> bytes:
        try:
            data = await client.read_gatt_char(uuid)
            _LOGGER.debug("Read %s → %s (%d bytes)", uuid[:8], data.hex(), len(data))
            return data
        except BleakError as e:
            _LOGGER.warning("Failed to read %s: %s", uuid[:8], e)
            return b"\x00\x00\x00\x00"

    async def _write_char(self, client: BleakClient, uuid: str, data: bytes) -> None:
        """Write characteristic — try without response first (matches App Inventor behaviour)."""
        _LOGGER.debug("Write %s → %s (%d bytes)", uuid[:8], data.hex(), len(data))
        try:
            # App Inventor BLE sends WriteCommand (no response) — try that first
            await client.write_gatt_char(uuid, data, response=False)
        except BleakError as e1:
            _LOGGER.debug("Write no-response failed (%s), trying with response", e1)
            try:
                await client.write_gatt_char(uuid, data, response=True)
            except BleakError as e2:
                _LOGGER.error("Failed to write %s: %s", uuid[:8], e2)

    # ── sync time to device ─────────────────────────────────────────────────

    async def async_sync_rtc(self) -> None:
        """Explicitly sync phone time to device RTC (call manually, not on every poll)."""
        async with self._lock:
            try:
                client = self._make_client()
                async with client:
                    now = datetime.now()
                    hour12 = now.hour % 12 or 12
                    ampm = 1 if now.hour >= 12 else 0

                    raw = await self._read_char(client, CHAR2_RTC_UUID)
                    v = bytes_to_int(raw)
                    v = set_field(v, *CHAR2_SECONDS, now.second)
                    v = set_field(v, *CHAR2_MINUTE,  now.minute)
                    v = set_field(v, *CHAR2_HOUR,    hour12)
                    v = set_field(v, *CHAR2_AMPM,    ampm)
                    v = set_field(v, *CHAR2_DAY,     now.day)
                    v = set_field(v, *CHAR2_MONTH,   now.month)
                    await self._write_char(client, CHAR2_RTC_UUID, int_to_bytes(v))
                    _LOGGER.info("RTC synced to %s", now.strftime("%H:%M:%S %d/%m"))
            except (BleakError, asyncio.TimeoutError) as e:
                _LOGGER.error("RTC sync failed: %s", e)

    # ── coordinator update ──────────────────────────────────────────────────

    async def _async_update_data(self) -> PetPianoData:
        # If a write action is already holding the lock, return cached data
        if self._lock.locked():
            _LOGGER.debug("BLE session busy — returning cached data")
            if self.data is not None:
                return self.data
            raise UpdateFailed("BLE session busy, no cached data yet")

        for attempt in range(3):
            try:
                async with self._lock:
                    return await self._do_read()
            except (BleakError, asyncio.TimeoutError) as e:
                err = str(e)
                _LOGGER.warning("Poll attempt %d/3 failed: %s", attempt + 1, err)
                if attempt < 2:
                    await asyncio.sleep(3 * (attempt + 1))   # 3 s, then 6 s
                else:
                    # All retries exhausted — keep old data, don't mark unavailable
                    if self.data is not None:
                        _LOGGER.warning("Using cached data after 3 failed attempts")
                        return self.data
                    raise UpdateFailed(f"BLE error: {e}") from e

        # Should never reach here
        raise UpdateFailed("Unexpected poll exit")

    async def _do_read(self) -> PetPianoData:
        """Single BLE session: connect, read all 4 chars, disconnect."""
        result = PetPianoData()
        client = self._make_client()
        async with client:
            _LOGGER.debug("Connected to PetPiano %s", self.address)

            raw1 = await self._read_char(client, CHAR1_SETTINGS_UUID)
            raw4 = await self._read_char(client, CHAR4_SETTINGS2_UUID)
            raw2 = await self._read_char(client, CHAR2_RTC_UUID)
            raw3 = await self._read_char(client, CHAR3_SCHEDULE_UUID)

        # Decode outside the connection (no need to stay connected)
        result.raw = {
            "CHAR1": raw1.hex(),
            "CHAR4": raw4.hex(),
            "CHAR2": raw2.hex(),
            "CHAR3": raw3.hex(),
        }
        _LOGGER.info(
            "PetPiano raw — CHAR1:%s CHAR4:%s CHAR2:%s CHAR3:%s",
            raw1.hex(), raw4.hex(), raw2.hex(), raw3.hex()
        )

        d1 = _decode_char1(raw1)
        result.mode           = d1["mode"]
        result.portions_today = d1["portions_today"]
        result.battery        = d1["battery"]
        result.power_source   = d1["power_source"]
        result.tutor_level    = d1["tutor_level"]
        result.motor_jam      = d1["motor_jam"]

        d4 = _decode_char4(raw4)
        result.volume           = d4["volume"]
        result.max_portions     = d4["max_portions"]
        result.meal_size_1      = d4["meal_size_1"]
        result.meal_size_2      = d4["meal_size_2"]
        result.schedule_enabled = d4["schedule_enabled"]
        result.melody_assist    = d4["melody_assist"]

        d2 = _decode_char2(raw2)
        result.rtc_hour   = d2["rtc_hour"]
        result.rtc_minute = d2["rtc_minute"]
        result.rtc_second = d2["rtc_second"]
        result.rtc_ampm   = d2["rtc_ampm"]
        result.rtc_day    = d2["rtc_day"]
        result.rtc_month  = d2["rtc_month"]
        result.food_level = d2["food_level"]

        d3 = _decode_char3(raw3)
        result.meal1_hour   = d3["meal1_hour"]
        result.meal1_minute = d3["meal1_minute"]
        result.meal1_ampm   = d3["meal1_ampm"]
        result.meal1_active = d3["meal1_pending"]
        result.meal2_hour   = d3["meal2_hour"]
        result.meal2_minute = d3["meal2_minute"]
        result.meal2_ampm   = d3["meal2_ampm"]
        result.meal2_active = d3["meal2_pending"]
        result.meal3_hour   = d3["meal3_hour"]
        result.meal3_minute = d3["meal3_minute"]
        result.meal3_ampm   = d3["meal3_ampm"]
        result.meal3_active = d3["meal3_pending"]

        return result

    # ── public write methods ────────────────────────────────────────────────

    async def _write_action(self, uuid: str, value: int) -> None:
        """Connect, read, modify, write — with lock."""
        async with self._lock:
            try:
                client = self._make_client()
                async with client:
                    raw = await self._read_char(client, uuid)
                    await self._write_char(client, uuid, int_to_bytes(value))
            except (BleakError, asyncio.TimeoutError) as e:
                _LOGGER.error("Write action failed: %s", e)

    async def async_dispense_now(self) -> None:
        """Trigger manual food dispense."""
        async with self._lock:
            try:
                client = self._make_client()
                async with client:
                    raw = await self._read_char(client, CHAR1_SETTINGS_UUID)
                    v = bytes_to_int(raw)
                    v = set_field(v, *CHAR1_MANUAL_DISPENSE, 1)
                    await self._write_char(client, CHAR1_SETTINGS_UUID, int_to_bytes(v))
                    _LOGGER.info("Manual dispense triggered")
            except (BleakError, asyncio.TimeoutError) as e:
                _LOGGER.error("Dispense failed: %s", e)

    async def async_set_volume(self, volume: int) -> None:
        """Set volume (0-7)."""
        async with self._lock:
            try:
                client = self._make_client()
                async with client:
                    raw = await self._read_char(client, CHAR4_SETTINGS2_UUID)
                    v = bytes_to_int(raw)
                    v = set_field(v, *CHAR4_VOLUME, max(0, min(7, volume)))
                    await self._write_char(client, CHAR4_SETTINGS2_UUID, int_to_bytes(v))
            except (BleakError, asyncio.TimeoutError) as e:
                _LOGGER.error("Set volume failed: %s", e)

    async def async_set_tutor_level(self, level: int) -> None:
        """Set tutor difficulty level (0-7) — controls how many keys cat must play."""
        async with self._lock:
            try:
                client = self._make_client()
                async with client:
                    raw = await self._read_char(client, CHAR1_SETTINGS_UUID)
                    v = bytes_to_int(raw)
                    v = set_field(v, *CHAR1_TUTOR_LEVEL, max(0, min(7, level)))
                    await self._write_char(client, CHAR1_SETTINGS_UUID, int_to_bytes(v))
                    _LOGGER.info("Tutor level set to %d", level)
            except (BleakError, asyncio.TimeoutError) as e:
                _LOGGER.error("Set tutor level failed: %s", e)

    async def async_set_schedule_enabled(self, enabled: bool) -> None:
        """Enable or disable the feeding schedule."""
        async with self._lock:
            try:
                client = self._make_client()
                async with client:
                    raw = await self._read_char(client, CHAR4_SETTINGS2_UUID)
                    v = bytes_to_int(raw)
                    v = set_field(v, *CHAR4_SCHEDULE_ENABLE, int(enabled))
                    await self._write_char(client, CHAR4_SETTINGS2_UUID, int_to_bytes(v))
            except (BleakError, asyncio.TimeoutError) as e:
                _LOGGER.error("Set schedule enabled failed: %s", e)

    async def async_set_mode(self, mode: int) -> None:
        """Set operating mode from APK-confirmed logic:
        - Tutor:   write g$CurrentLevel (bits 24-26) = 1-7, DON'T touch bits 0-1
        - Normal:  write g$CurrentLevel = 0, bits 0-1 = 0
        - Concert: write g$Mode (bits 0-1) = 1, g$CurrentLevel = 0
        """
        async with self._lock:
            try:
                client = self._make_client()
                async with client:
                    raw = await self._read_char(client, CHAR1_SETTINGS_UUID)
                    v = bytes_to_int(raw)
                    _LOGGER.info("Set mode %d: CHAR1 before=0x%08X", mode, v)

                    if mode == 1:  # Tutor — only write LEVEL, keep bits 0-1 unchanged
                        level = get_field(v, *CHAR1_TUTOR_LEVEL)
                        if level == 0:
                            level = 1
                        v = set_field(v, *CHAR1_TUTOR_LEVEL, level)
                        # Do NOT change CHAR1_MODE (bits 0-1)
                    elif mode == 2:  # Concert
                        v = set_field(v, *CHAR1_MODE, 1)    # bits 0-1 = 1
                        v = set_field(v, *CHAR1_TUTOR_LEVEL, 0)  # clear level
                    else:  # Normal (mode == 0)
                        v = set_field(v, *CHAR1_MODE, 0)    # bits 0-1 = 0
                        v = set_field(v, *CHAR1_TUTOR_LEVEL, 0)  # clear level

                    _LOGGER.info("Set mode %d: CHAR1 writing=0x%08X", mode, v)
                    await self._write_char(client, CHAR1_SETTINGS_UUID, int_to_bytes(v))
                    _LOGGER.info("Set mode %d: write done", mode)
            except (BleakError, asyncio.TimeoutError) as e:
                _LOGGER.error("Set mode failed: %s", e)

    async def async_set_meal_active(self, meal: int, active: bool) -> None:
        """Enable or disable a meal slot (meal=1,2,3)."""
        meal_active_fields = {
            1: CHAR3_MEAL1_ACTIVE,
            2: CHAR3_MEAL2_ACTIVE,
            3: CHAR3_MEAL3_ACTIVE,
        }
        field = meal_active_fields.get(meal)
        if not field:
            return
        async with self._lock:
            try:
                client = self._make_client()
                async with client:
                    raw = await self._read_char(client, CHAR3_SCHEDULE_UUID)
                    v = bytes_to_int(raw)
                    v = set_field(v, *field, int(active))
                    await self._write_char(client, CHAR3_SCHEDULE_UUID, int_to_bytes(v))
                    _LOGGER.info("Meal %d active=%s", meal, active)
            except (BleakError, asyncio.TimeoutError) as e:
                _LOGGER.error("Set meal active failed: %s", e)
