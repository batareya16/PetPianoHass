"""Pet Piano BLE Integration — Constants."""

DOMAIN = "pet_piano"
DEVICE_NAME = "PetPiano"

# BLE UUIDs
SERVICE_UUID       = "60462f12-9543-9999-12c8-58b459a2712d"
CHAR1_SETTINGS_UUID  = "34333333-2222-2222-1111-111100000000"
CHAR4_SETTINGS2_UUID = "35333333-2222-2222-1111-111100000000"
CHAR2_RTC_UUID       = "36333333-2222-2222-1111-111100000000"
CHAR3_SCHEDULE_UUID  = "37333333-2222-2222-1111-111100000000"

# ── Packet helpers ──────────────────────────────────────────────────────────
# 4 bytes, big-endian: [bits31-24, bits23-16, bits15-8, bits7-0]

def bytes_to_int(data: bytes) -> int:
    return int.from_bytes(data[:4], byteorder="big")

def int_to_bytes(value: int) -> bytes:
    return value.to_bytes(4, byteorder="big")

def get_field(value: int, bit_shift: int, mask: int) -> int:
    return (value & mask) >> bit_shift

def set_field(value: int, bit_shift: int, mask: int, new_val: int) -> int:
    return (value & ~mask) | ((new_val << bit_shift) & mask)


# ── CHAR1 (34333333) — Settings 1 ──────────────────────────────────────────
# Calibrated from real device data 0x00833FD0 (wall power, 12 portions, Normal mode)
CHAR1_MODE            = (0,  0x00000003)  # 2 bits: WRITE command (0=Normal,1=Tutor,2=Concert)
CHAR1_MODE_TUTOR      = (15, 0x00008000)  # 1 bit:  READ status — 1 = currently in Tutor mode
# Note: Concert status bit TBD (need raw data after Concert switch)
CHAR1_BATTERY         = (8,  0x00003F00)  # 6 bits: battery 0-63 (63=100%, wall power)
CHAR1_PORTIONS_TODAY  = (14, 0x003FC000)  # 8 bits: portions dispensed today (confirmed: was 12)
CHAR1_POWER_SOURCE    = (23, 0x00800000)  # 1 bit:  1=wall adapter, 0=battery
CHAR1_TUTOR_LEVEL     = (24, 0x07000000)  # 3 bits: tutor difficulty 0-7
CHAR1_MOTOR_JAM       = (30, 0x40000000)  # 1 bit:  motor jammed (read-only)
CHAR1_MANUAL_DISPENSE = (31, 0x80000000)  # 1 bit:  trigger manual dispense (write)

# ── CHAR4 (35333333) — Settings 2 ──────────────────────────────────────────
# Decoded from 0x294B2711
CHAR4_BIRTH_DAY       = (0,  0x0000001F)  # 5 bits: pet birthday day 1-31
CHAR4_MELODY_ASSIST   = (2,  0x00000004)  # 1 bit:  melody assist on/off
CHAR4_VOLUME          = (3,  0x00000038)  # 3 bits: volume 0-7
CHAR4_BIRTH_MONTH     = (5,  0x000001E0)  # 4 bits: pet birthday month 1-12
CHAR4_MAX_PORTIONS    = (6,  0x00003FC0)  # 8 bits: max portions per day 0-255
CHAR4_MEAL_SIZE_1     = (17, 0x003E0000)  # 5 bits: meal size 1 (0-31)
CHAR4_MEAL_SIZE_2     = (22, 0x07C00000)  # 5 bits: meal size 2 (0-31)
CHAR4_SCHEDULE_ENABLE = (31, 0x80000000)  # 1 bit:  schedule enabled

# ── CHAR2 (36333333) — RTC ─────────────────────────────────────────────────
# Calibrated from real device data 0x6965C3AB (12:14:43 PM, May 18)
CHAR2_SECONDS    = (0,  0x0000003F)  # 6 bits: seconds 0-59  (decoded: 43) ✓
CHAR2_MINUTE     = (6,  0x00000FC0)  # 6 bits: minutes 0-59  (decoded: 14) ✓
CHAR2_HOUR       = (12, 0x0000F000)  # 4 bits: hours 1-12   (decoded: 12) ✓ FIXED was (10,0x3C00)
CHAR2_AMPM       = (16, 0x00010000)  # 1 bit:  0=AM, 1=PM    (decoded: 1=PM) ✓
CHAR2_DAY        = (17, 0x003E0000)  # 5 bits: day 1-31      (decoded: 18) ✓
CHAR2_MONTH      = (22, 0x03C00000)  # 4 bits: month 1-12    (decoded: 5=May) ✓
CHAR2_FOOD_LEVEL = (26, 0x1C000000)  # 3 bits: food level 0-7 (decoded: 2) ✓

# ── CHAR3 (37333333) — Schedule ────────────────────────────────────────────
# Calibrated from real device data 0x00163998
# Structure: 8 bits per meal slot [2-min | 4-hour | 1-ampm | 1-active]
# Minutes: 0=:00, 1=:15, 2=:30, 3=:45
CHAR3_MEAL1_MINUTE = (0,  0x00000003)  # decoded: 0 → :00
CHAR3_MEAL1_HOUR   = (2,  0x0000003C)  # decoded: 6 → 6 AM ✓
CHAR3_MEAL1_AMPM   = (6,  0x00000040)  # decoded: 0 → AM ✓
CHAR3_MEAL1_ACTIVE = (7,  0x00000080)  # decoded: 1 → active ✓

CHAR3_MEAL2_MINUTE = (8,  0x00000300)  # decoded: 1 → :15
CHAR3_MEAL2_HOUR   = (10, 0x00003C00)  # decoded: 14 (garbage, meal inactive) FIXED was (12,...)
CHAR3_MEAL2_AMPM   = (14, 0x00004000)  # decoded: 0 → AM
CHAR3_MEAL2_ACTIVE = (15, 0x00008000)  # decoded: 0 → inactive ✓   FIXED was (28,0x10000000)

CHAR3_MEAL3_MINUTE = (16, 0x00030000)  # decoded: 2 → :30
CHAR3_MEAL3_HOUR   = (18, 0x003C0000)  # decoded: 5 → 5 AM
CHAR3_MEAL3_AMPM   = (22, 0x00400000)  # decoded: 0 → AM
CHAR3_MEAL3_ACTIVE = (23, 0x00800000)  # decoded: 0 → inactive ✓   FIXED was (29,0x20000000)

QUARTER_HOUR_MAP = {0: 0, 1: 15, 2: 30, 3: 45}
QUARTER_HOUR_REVERSE = {0: 0, 15: 1, 30: 2, 45: 3}

MODE_MAP = {0: "Normal", 1: "Tutor", 2: "Concert"}
