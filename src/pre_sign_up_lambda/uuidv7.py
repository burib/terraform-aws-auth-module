# Save this code in a file, e.g., uuidv7.py

import time
import random
import uuid # Use the standard library uuid module

# Use SystemRandom for cryptographically secure random numbers
_SYSTEM_RANDOM = random.SystemRandom()

def uuidv7() -> uuid.UUID:
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

    # Construct the 128-bit integer according to RFC 9562 layout:
    uuid_int = (unix_ts_ms << 80)  # Place 48-bit timestamp at the most significant position
    uuid_int |= (VERSION << 76)    # Place 4-bit version
    uuid_int |= (rand_a << 64)     # Place 12-bit rand_a
    uuid_int |= (VARIANT << 62)    # Place 2-bit variant
    uuid_int |= rand_b             # Place 62-bit rand_b in the least significant position

    # Return as a standard uuid.UUID object, letting it handle formatting
    return uuid.UUID(int=uuid_int)

# --- Example Usage (optional, for testing) ---
if __name__ == "__main__":
    id1 = uuidv7()
    id2 = uuidv7()
    print(f"UUIDv7 (RFC 9562 compliant): {id1}")
    print(f"UUIDv7 (RFC 9562 compliant): {id2}")
    print(f"Is id1 < id2 (time sortable)? {id1 < id2}") # Should generally be true if generated sequentially
