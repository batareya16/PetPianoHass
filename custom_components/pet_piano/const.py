"""Pet Piano BLE Integration — Constants."""

DOMAIN = "pet_piano"
DEVICE_NAME = "PetPiano"

# BLE UUIDs
SERVICE_UUID       = "60462f12-9543-9999-12c8-58b459a2712d"
CHAR1_SETTINGS_UUID  = "34333333-2222-2222-1111-111100000000"  # Settings 1 (status, mode)
CHAR4_SETTINGS2_UUID = "35333333-2222-2222-1111-111100000000"  # Settings 2 (sound, portions)
CHAR2_RTC_UUID       = "36333333-2222-2222-1111-111100000000"  # Real-time clock
CHAR3_SCHEDULE_UUID  = "37333333-2222-2222-1111-111100000000"  # Feeding schedule

# ── Packet helpers ──────────────────────────────────────────────────────────
# 4 bytes, big-endian: [bits31-24, bits23-16, bits15-8, bits7-0]

def bytes_to_int(data: bytes) -> int:
    """Convert 4-byte big-endian BLE response to 32-bit int."""
    return int.from_bytes(data[:4], byteorder="big")

def int_to_bytes(value: int) -> bytes:
    """Convert 32-bit int to 4-byte big-endian for WriteBytes."""
    return value.to_bytes(4, byteorder="big")

def get_field(value: int, bit_shift: int, mask: int) -> int:
    """Extract a bit-field from combined 32-bit value."""
    return (value & mask) >> bit_shift

def set_field(value: int, bit_shift: int, mask: int, new_val: int) -> int:
    """Write a bit-field into combined 32-bit value."""
    return (value & ~mask) | ((new_val << bit_shift) & mask)


# ── CHAR1 (34333333) — Settings 1 ──────────────────────────────────────────
# [bit_shift, mask]
CHAR1_MODE              = (0,  0x00000003)  # 2 bits: 0=Normal,1=Tutor,2=Concert
CHAR1_PORTIONS_TODAY    = (14, 0x003FC000)  # 8 bits: portions dispensed today (read-only)
CHAR1_BATTERY           = (21, 0x0FE00000)  # 7 bits: battery level 0-100 (read-only)
CHAR1_POWER_SOURCE      = (28, 0x10000000)  # 1 bit:  0=battery, 1=wall adapter (read-only)
CHAR1_DOUBLE_NOTE       = (29, 0x20000000)  # 1 bit:  double note on/off
CHAR1_MOTOR_JAM         = (30, 0x40000000)  # 1 bit:  motor jam (read-only, error flag)
CHAR1_MANUAL_DISPENSE   = (31, 0x80000000)  # 1 bit:  trigger manual dispense (write)

# ── CHAR4 (35333333) — Settings 2 ──────────────────────────────────────────
CHAR4_BIRTH_DAY         = (0,  0x0000001F)  # 5 bits: pet birthday day 1-31
CHAR4_MELODY_ASSIST     = (2,  0x00000004)  # 1 bit:  melody assist on/off
CHAR4_VOLUME            = (3,  0x00000038)  # 3 bits: volume 0-7
CHAR4_BIRTH_MONTH       = (5,  0x000001E0)  # 4 bits: pet birthday month 1-12
CHAR4_MAX_PORTIONS      = (6,  0x00003FC0)  # 8 bits: max portions per day 0-255
CHAR4_MEAL_SIZE_1       = (17, 0x003E0000)  # 5 bits: meal size 1 (0-31)
CHAR4_MEAL_SIZE_2       = (22, 0x07C00000)  # 5 bits: meal size 2 (0-31)
CHAR4_SCHEDULE_ENABLE   = (31, 0x80000000)  # 1 bit:  schedule enabled

# ── CHAR2 (36333333) — RTC ─────────────────────────────────────────────────
CHAR2_SECONDS   = (0,  0x0000003F)  # 6 bits: seconds 0-59
CHAR2_MINUTE    = (6,  0x00000FC0)  # 6 bits: minutes 0-59
CHAR2_HOUR      = (10, 0x00003C00)  # 4 bits: hours 1-12
CHAR2_AMPM      = (16, 0x00010000)  # 1 bit:  0=AM, 1=PM
CHAR2_DAY       = (17, 0x003E0000)  # 5 bits: day 1-31
CHAR2_MONTH     = (22, 0x03C00000)  # 4 bits: month 1-12
CHAR2_FOOD_LEVEL= (26, 0x1C000000)  # 3 bits: food level in hopper 0-7

# ── CHAR3 (37333333) — Schedule ────────────────────────────────────────────
# Minutes encoded as quarter-hours: 0=:00, 1=:15, 2=:30, 3=:45
CHAR3_MEAL1_MINUTE  = (0,  0x00000003)  # 2 bits
CHAR3_MEAL1_HOUR    = (2,  0x0000003C)  # 4 bits: 1-12
CHAR3_MEAL1_AMPM    = (6,  0x00000040)  # 1 bit
CHAR3_MEAL1_ACTIVE  = (7,  0x00000080)  # 1 bit:  meal 1 enabled

CHAR3_MEAL2_MINUTE  = (8,  0x00000300)  # 2 bits
CHAR3_MEAL2_HOUR    = (12, 0x00003C00)  # 4 bits: 1-12 (wait—overlaps; needs real data)
CHAR3_MEAL2_AMPM    = (14, 0x00004000)  # 1 bit
CHAR3_MEAL2_ACTIVE  = (28, 0x10000000)  # 1 bit

CHAR3_MEAL3_MINUTE  = (16, 0x00030000)  # 2 bits
CHAR3_MEAL3_HOUR    = (18, 0x003C0000)  # 4 bits
CHAR3_MEAL3_AMPM    = (22, 0x00400000)  # 1 bit
CHAR3_MEAL3_ACTIVE  = (29, 0x20000000)  # 1 bit

CHAR3_DOUBLE_NOTE   = (31, 0x80000000)  # 1 bit (also mirrored here)

QUARTER_HOUR_MAP = {0: 0, 1: 15, 2: 30, 3: 45}
QUARTER_HOUR_REVERSE = {0: 0, 15: 1, 30: 2, 45: 3}

MODE_MAP = {0: "Normal", 1: "Tutor", 2: "Concert"}
