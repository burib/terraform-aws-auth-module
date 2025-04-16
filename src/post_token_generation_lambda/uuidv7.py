# Save this code in a file, e.g., custom_uuid.py

import time
import random
import uuid # Use the standard library uuid module

# Use SystemRandom for cryptographically secure random numbers
_SYSTEM_RANDOM = random.SystemRandom()

def uuid7() -> uuid.UUID:
    """
    Generates a UUID Version 7 (time-ordered) according to RFC 9562.

    Returns:
        uuid.UUID: A new UUIDv7 object.

    Layout:
    | unixts_ms (48 bits) | ver (4) | rand_a (12) | var (2) | rand_b (62) |
    | ------------------- | ------- | ----------- | ------- | ----------- |
    |        Most Significant Bits               | Least Significant Bits|
    """
    # Get the current time in nanoseconds since the Unix epoch
    nanoseconds = time.time_ns()
    # Convert to milliseconds - the core of UUIDv7 timestamp
    unix_ts_ms = nanoseconds // 1_000_000

    # Generate random bits for the 'rand_a' and 'rand_b' sections.
    # rand_a (12 bits): Per RFC, can be random or a counter for monotonicity.
    #                   Using random here for simplicity and compliance.
    rand_a = _SYSTEM_RANDOM.getrandbits(12)
    # rand_b (62 bits): Remaining random bits for uniqueness.
    rand_b = _SYSTEM_RANDOM.getrandbits(62)

    # Version (ver) is 7 (0b0111)
    VERSION = 0x7
    # Variant (var) is RFC 4122 (0b10)
    VARIANT = 0x2

    # Construct the 128-bit integer:
    uuid_int = (unix_ts_ms << 80)  # Shift timestamp 80 bits left
    uuid_int |= (VERSION << 76)    # Place version bits (4 bits)
    uuid_int |= (rand_a << 64)     # Place rand_a bits (12 bits)
    uuid_int |= (VARIANT << 62)    # Place variant bits (2 bits)
    uuid_int |= rand_b             # Place rand_b bits (62 bits)

    # Return as a standard uuid.UUID object
    return uuid.UUID(int=uuid_int)

# --- Example Usage (optional, for testing) ---
if __name__ == "__main__":
    id1 = uuid7()
    id2 = uuid7()
    print(f"UUIDv7 (RFC 9562 compliant): {id1}")
    print(f"UUIDv7 (RFC 9562 compliant): {id2}")
    print(f"Is id1 < id2 (time sortable)? {id1 < id2}") # Should generally be true if generated sequentially
