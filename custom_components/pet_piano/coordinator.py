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
    CHAR2_AMPM, CHAR2_DAY, CHAR2_MONTH,
    CHAR3_MEAL1_MINUTE, CHAR3_MEAL1_HOUR, CHAR3_MEAL1_AMPM, CHAR3_MEAL1_ACTIVE,
    CHAR3_MEAL2_MINUTE, CHAR3_MEAL2_HOUR, CHAR3_MEAL2_AMPM, CHAR3_MEAL2_ACTIVE,
    CHAR3_MEAL3_MINUTE, CHAR3_MEAL3_HOUR, CHAR3_MEAL3_AMPM, CHAR3_MEAL3_ACTIVE,
    QUARTER_HOUR_MAP, MODE_MAP,
)

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=60)   # poll every 60 s
WRITE_RETRIES = 3                        # how many times to retry a write
WRITE_RETRY_DELAY = 3.0                  # seconds between write retries
BLE_CONNECT_TIMEOUT = 30.0              # seconds for BLE connect + service discovery
BLE_READY_DELAY = 0.8                   # seconds to wait after connect before first GATT op


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

        # Derived — None if grams_per_portion not configured yet
        self.grams_today: float | None = None
        self.tutor_level: int = 0      # 0-7: difficulty / keys required (writable)

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

    def __init__(self, hass: HomeAssistant, address: str, grams_per_portion: float | None = None) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.address = address
        self.grams_per_portion: float = grams_per_portion
        self._lock = asyncio.Lock()
        self._last_tutor_level: int = 1  # remember level across mode switches
        # Cache of last known raw int values per characteristic UUID.
        # Used by write methods so we don't need to re-read before every write.
        self._cached_raw: dict[str, int] = {}

    # ── internal BLE helpers ────────────────────────────────────────────────

    def _get_ble_device(self) -> BLEDevice:
        ble_device: BLEDevice | None = async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )
        if ble_device is None:
            raise UpdateFailed(f"PetPiano ({self.address}) not in BLE scanner cache")
        return ble_device

    async def _connect(self) -> BleakClient:
        """Connect to PetPiano and return a connected (but not yet used) client.

        Uses the habluetooth-wrapped BLEDevice from HA's scanner cache.
        habluetooth already handles scanner/GATT conflict on Linux/BlueZ
        (it pauses passive scanning during connection), so we don't need
        bleak_retry_connector on top.  A plain BleakClient with a generous
        timeout is the most compatible approach for cheap BLE devices.
        """
        ble_device = self._get_ble_device()
        client = BleakClient(ble_device, timeout=BLE_CONNECT_TIMEOUT)
        await client.connect()
        return client

    async def _read_char(self, client: BleakClient, uuid: str) -> bytes:
        """Read a characteristic — raises BleakError on failure (let the retry loop handle it)."""
        data = await client.read_gatt_char(uuid)
        _LOGGER.debug("Read %s → %s (%d bytes)", uuid[:8], data.hex(), len(data))
        return data

    @staticmethod
    async def _safe_disconnect(client: BleakClient) -> None:
        """Disconnect quietly — device may have already closed the link."""
        try:
            await client.disconnect()
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("Disconnect error (ignored): %s", exc)

    async def _write_cached(self, uuid: str, new_value: int) -> bool:
        """Write a characteristic value using cached state (no pre-read needed).

        Uses plain BleakClient with habluetooth-wrapped device from HA's scanner.
        habluetooth pauses the passive BLE scan during connection, preventing
        ATT 0x0e scanner/GATT conflicts.  Manual connect/disconnect (not
        async with) so EOFError during cleanup doesn't mask a successful write.
        Retries up to WRITE_RETRIES times.  Returns True on success.
        The caller is responsible for holding self._lock.
        """
        for attempt in range(1, WRITE_RETRIES + 1):
            client = None
            try:
                client = await self._connect()
                await asyncio.sleep(BLE_READY_DELAY)
                await client.write_gatt_char(
                    uuid, int_to_bytes(new_value), response=False
                )
                self._cached_raw[uuid] = new_value  # keep cache in sync
                _LOGGER.info(
                    "Written %s → 0x%08X (attempt %d/%d)",
                    uuid[:8], new_value, attempt, WRITE_RETRIES,
                )
                return True
            except (BleakError, asyncio.TimeoutError, UpdateFailed) as exc:
                _LOGGER.warning(
                    "Write %s attempt %d/%d failed: %s",
                    uuid[:8], attempt, WRITE_RETRIES, exc,
                )
                if attempt < WRITE_RETRIES:
                    await asyncio.sleep(WRITE_RETRY_DELAY)
            finally:
                if client is not None:
                    await self._safe_disconnect(client)
        _LOGGER.error("Write %s failed after %d attempts", uuid[:8], WRITE_RETRIES)
        return False

    # ── sync time to device ─────────────────────────────────────────────────

    async def async_sync_rtc(self) -> None:
        """Explicitly sync HA time to device RTC."""
        now = datetime.now()
        hour12 = now.hour % 12 or 12
        ampm = 1 if now.hour >= 12 else 0
        v = self._cached(CHAR2_RTC_UUID)
        v = set_field(v, *CHAR2_SECONDS, now.second)
        v = set_field(v, *CHAR2_MINUTE,  now.minute)
        v = set_field(v, *CHAR2_HOUR,    hour12)
        v = set_field(v, *CHAR2_AMPM,    ampm)
        v = set_field(v, *CHAR2_DAY,     now.day)
        v = set_field(v, *CHAR2_MONTH,   now.month)
        self._fire_write(CHAR2_RTC_UUID, v)
        _LOGGER.info("RTC sync queued for %s", now.strftime("%H:%M:%S %d/%m"))

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
            except (BleakError, asyncio.TimeoutError, UpdateFailed) as e:
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
        client = await self._connect()
        try:
            _LOGGER.debug("Connected to PetPiano %s", self.address)
            # PetPiano accepts the connection but isn't ready for GATT reads
            # immediately — causes ATT 0x0e if we read too fast.
            await asyncio.sleep(BLE_READY_DELAY)

            raw1 = await self._read_char(client, CHAR1_SETTINGS_UUID)
            raw4 = await self._read_char(client, CHAR4_SETTINGS2_UUID)
            raw2 = await self._read_char(client, CHAR2_RTC_UUID)
            raw3 = await self._read_char(client, CHAR3_SCHEDULE_UUID)
        finally:
            await self._safe_disconnect(client)

        # Update raw-int cache so write methods can use it without re-reading
        self._cached_raw[CHAR1_SETTINGS_UUID] = bytes_to_int(raw1)
        self._cached_raw[CHAR4_SETTINGS2_UUID] = bytes_to_int(raw4)
        self._cached_raw[CHAR2_RTC_UUID]       = bytes_to_int(raw2)
        self._cached_raw[CHAR3_SCHEDULE_UUID]  = bytes_to_int(raw3)

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
        result.grams_today    = (
            round(result.portions_today * self.grams_per_portion, 1)
            if self.grams_per_portion is not None else None
        )

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
    # Pattern:
    #   1. Build new value from _cached_raw (no extra BLE read needed)
    #   2. Update coordinator.data + call _optimistic_update() RIGHT NOW
    #      so the UI reflects the change before BLE even starts
    #   3. Kick off _write_cached in background (hass.async_create_task)
    #      so the caller returns immediately and the BLE retry loop doesn't
    #      block the HA event loop from the user's perspective

    def _cached(self, uuid: str) -> int:
        """Return last known raw int for a characteristic (0 if never read)."""
        return self._cached_raw.get(uuid, 0)

    def _optimistic_update(self) -> None:
        """Push current coordinator.data immediately to all listeners."""
        if self.data is not None:
            self.async_set_updated_data(self.data)

    def _fire_write(self, uuid: str, value: int) -> None:
        """Schedule a BLE write as a background task (non-blocking)."""
        async def _task() -> None:
            async with self._lock:
                await self._write_cached(uuid, value)
        self.hass.async_create_task(_task())

    async def async_dispense_now(self) -> None:
        """Trigger manual food dispense."""
        v = set_field(self._cached(CHAR1_SETTINGS_UUID), *CHAR1_MANUAL_DISPENSE, 1)
        _LOGGER.info("Manual dispense triggered")
        self._fire_write(CHAR1_SETTINGS_UUID, v)

    async def async_set_volume(self, volume: int) -> None:
        """Set volume (0-7)."""
        clamped = max(0, min(7, volume))
        v = set_field(self._cached(CHAR4_SETTINGS2_UUID), *CHAR4_VOLUME, clamped)
        # Optimistic: update UI immediately
        if self.data is not None:
            self.data.volume = clamped
            self._optimistic_update()
        self._fire_write(CHAR4_SETTINGS2_UUID, v)

    async def async_set_tutor_level(self, level: int) -> None:
        """Set tutor difficulty level (0-7) — controls how many keys cat must play."""
        clamped = max(0, min(7, level))
        v = set_field(self._cached(CHAR1_SETTINGS_UUID), *CHAR1_TUTOR_LEVEL, clamped)
        if clamped > 0:
            self._last_tutor_level = clamped
        if self.data is not None:
            self.data.tutor_level = clamped
            self._optimistic_update()
        self._fire_write(CHAR1_SETTINGS_UUID, v)
        _LOGGER.info("Tutor level queued: %d", clamped)

    async def async_set_schedule_enabled(self, enabled: bool) -> None:
        """Enable or disable the feeding schedule."""
        v = set_field(self._cached(CHAR4_SETTINGS2_UUID), *CHAR4_SCHEDULE_ENABLE, int(enabled))
        if self.data is not None:
            self.data.schedule_enabled = enabled
            self._optimistic_update()
        self._fire_write(CHAR4_SETTINGS2_UUID, v)

    async def async_set_mode(self, mode: int) -> None:
        """Set operating mode from APK-confirmed logic:
        - Tutor:   write g$CurrentLevel (bits 24-26) = 1-7, clear bits 0-1
        - Normal:  write g$CurrentLevel = 0, bits 0-1 = 0
        - Concert: write g$Mode (bits 0-1) = 1, g$CurrentLevel = 0
        """
        v = self._cached(CHAR1_SETTINGS_UUID)
        _LOGGER.info("Set mode %d: CHAR1 cached=0x%08X", mode, v)

        # Always clear ManualDispense — APK (p$ResetDinnerBell) does this explicitly
        v = set_field(v, *CHAR1_MANUAL_DISPENSE, 0)

        if mode == 1:  # Tutor
            v = set_field(v, *CHAR1_MODE, 0)
            level = self._last_tutor_level or 1
            v = set_field(v, *CHAR1_TUTOR_LEVEL, max(1, min(7, level)))
        elif mode == 2:  # Concert
            current_level = get_field(v, *CHAR1_TUTOR_LEVEL)
            if current_level > 0:
                self._last_tutor_level = current_level
            v = set_field(v, *CHAR1_MODE, 1)
            v = set_field(v, *CHAR1_TUTOR_LEVEL, 0)
        else:  # Normal
            current_level = get_field(v, *CHAR1_TUTOR_LEVEL)
            if current_level > 0:
                self._last_tutor_level = current_level
            v = set_field(v, *CHAR1_MODE, 0)
            v = set_field(v, *CHAR1_TUTOR_LEVEL, 0)

        _LOGGER.info("Set mode %d: CHAR1 queuing=0x%08X", mode, v)
        # Optimistic update first
        if self.data is not None:
            self.data.mode = mode
            self.data.tutor_level = (self._last_tutor_level or 1) if mode == 1 else 0
            self._optimistic_update()
        self._fire_write(CHAR1_SETTINGS_UUID, v)

    async def async_set_meal_time(self, meal: int, hour12: int, minute_qh: int, ampm: int) -> None:
        """Set meal time. hour12=1-12, minute_qh=0/15/30/45, ampm=0/1."""
        from .const import (
            CHAR3_MEAL1_HOUR, CHAR3_MEAL1_MINUTE, CHAR3_MEAL1_AMPM,
            CHAR3_MEAL2_HOUR, CHAR3_MEAL2_MINUTE, CHAR3_MEAL2_AMPM,
            CHAR3_MEAL3_HOUR, CHAR3_MEAL3_MINUTE, CHAR3_MEAL3_AMPM,
            QUARTER_HOUR_REVERSE,
        )
        fields = {
            1: (CHAR3_MEAL1_HOUR, CHAR3_MEAL1_MINUTE, CHAR3_MEAL1_AMPM),
            2: (CHAR3_MEAL2_HOUR, CHAR3_MEAL2_MINUTE, CHAR3_MEAL2_AMPM),
            3: (CHAR3_MEAL3_HOUR, CHAR3_MEAL3_MINUTE, CHAR3_MEAL3_AMPM),
        }
        if meal not in fields:
            return
        f_hour, f_min, f_ampm = fields[meal]
        qh = QUARTER_HOUR_REVERSE.get(minute_qh, 0)
        v = self._cached(CHAR3_SCHEDULE_UUID)
        v = set_field(v, *f_hour, max(1, min(12, hour12)))
        v = set_field(v, *f_min,  qh)
        v = set_field(v, *f_ampm, ampm)
        if self.data is not None:
            setattr(self.data, f"meal{meal}_hour",   hour12)
            setattr(self.data, f"meal{meal}_minute", minute_qh)
            setattr(self.data, f"meal{meal}_ampm",   ampm)
            self._optimistic_update()
        self._fire_write(CHAR3_SCHEDULE_UUID, v)
        _LOGGER.info("Meal %d time queued: %02d:%02d %s", meal, hour12, minute_qh, "PM" if ampm else "AM")

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
        v = set_field(self._cached(CHAR3_SCHEDULE_UUID), *field, int(active))
        if self.data is not None:
            setattr(self.data, f"meal{meal}_active", active)
            self._optimistic_update()
        self._fire_write(CHAR3_SCHEDULE_UUID, v)
        _LOGGER.info("Meal %d active=%s queued", meal, active)
