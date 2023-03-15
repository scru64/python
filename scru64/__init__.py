"""SCRU64: Sortable, Clock-based, Realm-specifically Unique identifier"""

from __future__ import annotations

__all__ = [
    "new",
    "new_string",
    "new_async",
    "new_string_async",
    "Scru64Id",
    "Scru64Generator",
]

import asyncio
import datetime
import os
import random
import re
import threading
import time
import typing

# Maximum valid value (i.e., `zzzzzzzzzzzz`).
SCRU64_INT_MAX = 36**12 - 1

# Total size in bits of the `node_id` and `counter` fields.
NODE_CTR_SIZE = 24

# Maximum valid value of the `timestamp` field.
TIMESTAMP_MAX = SCRU64_INT_MAX >> NODE_CTR_SIZE

# Maximum valid value of the combined `node_ctr` field.
NODE_CTR_MAX = (1 << NODE_CTR_SIZE) - 1

# Digit characters used in the Base36 notation.
DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"


class Scru64Id:
    """Represents a SCRU64 ID."""

    __slots__ = "_value"

    def __int__(self) -> int:
        """Returns the integer representation."""
        return self._value

    def __init__(self, int_value: int) -> None:
        """Creates an object from a 64-bit integer."""
        self._value = int_value
        if not (0 <= int_value <= SCRU64_INT_MAX):
            raise ValueError("out of valid integer range")

    def __str__(self) -> str:
        """Returns the 12-digit canonical string representation."""
        buffer = ["0"] * 12
        n = self._value
        for i in range(12):
            (n, rem) = divmod(n, 36)
            buffer[11 - i] = DIGITS[rem]
        return "".join(buffer)

    @classmethod
    def from_str(cls, str_value: str) -> Scru64Id:
        """Creates an object from a 12-digit string representation."""
        if re.fullmatch(r"[0-9A-Za-z]{12}", str_value) is None:
            raise ValueError("invalid string representation")
        return cls(int(str_value, 36))

    @property
    def timestamp(self) -> int:
        """Returns the `timestamp` field value."""
        return self._value >> NODE_CTR_SIZE

    @property
    def node_ctr(self) -> int:
        """
        Returns the `node_id` and `counter` field values combined as a single integer.
        """
        return self._value & NODE_CTR_MAX

    @classmethod
    def from_parts(cls, timestamp: int, node_ctr: int) -> Scru64Id:
        """
        Creates a value from the `timestamp` and the combined `node_ctr` field value.
        """
        if timestamp < 0 or timestamp > TIMESTAMP_MAX:
            raise ValueError("`timestamp` out of range")
        if node_ctr < 0 or node_ctr > NODE_CTR_MAX:
            raise ValueError("`node_ctr` out of range")
        return cls(timestamp << NODE_CTR_SIZE | node_ctr)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(0x{self._value:016X})"

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, self.__class__):
            return NotImplemented
        return self._value == value._value

    def __hash__(self) -> int:
        return hash(self._value)

    def __lt__(self, value: object) -> bool:
        if not isinstance(value, self.__class__):
            return NotImplemented
        return self._value < value._value

    def __le__(self, value: object) -> bool:
        if not isinstance(value, self.__class__):
            return NotImplemented
        return self._value <= value._value

    def __gt__(self, value: object) -> bool:
        if not isinstance(value, self.__class__):
            return NotImplemented
        return self._value > value._value

    def __ge__(self, value: object) -> bool:
        if not isinstance(value, self.__class__):
            return NotImplemented
        return self._value >= value._value


class Scru64Generator:
    """
    Represents a SCRU64 ID generator.

    The generator offers six different methods to generate a SCRU64 ID:

    | Flavor                  | Timestamp | Thread- | On big clock rewind  |
    | ----------------------- | --------- | ------- | -------------------- |
    | generate                | Now       | Safe    | Rewinds state        |
    | generate_no_rewind      | Now       | Safe    | Returns `None`       |
    | generate_or_wait        | Now       | Safe    | Waits (blocking)     |
    | generate_or_wait_async  | Now       | Safe    | Waits (non-blocking) |
    | generate_core           | Argument  | Unsafe  | Rewinds state        |
    | generate_core_no_rewind | Argument  | Unsafe  | Returns `None`       |

    Each method returns monotonically increasing IDs unless a timestamp provided is
    significantly (by ~10 seconds or more) smaller than the one embedded in the
    immediately preceding ID. If such a significant clock rollback is detected, (i) the
    standard `generate` rewinds the generator state and returns a new ID based on the
    current timestamp; (ii) `no_rewind` variants keep the state untouched and return
    `None`; and, (iii) `or_wait` functions sleep and wait for the next timestamp tick.
    `core` functions offer low-level thread-unsafe primitives.
    """

    def __init__(self, node_id: int, node_id_size: int) -> None:
        """
        Creates a generator with a node configuration.

        The `node_id` must fit in `node_id_size` bits, where `node_id_size` ranges from
        1 to 23, inclusive.
        """
        if node_id_size <= 0 or node_id_size >= NODE_CTR_SIZE:
            raise ValueError("`node_id_size` must range from 1 to 23")
        if node_id < 0 or node_id >= (1 << node_id_size):
            raise ValueError("`node_id` must fit in `node_id_size` bits")

        self._counter_size = NODE_CTR_SIZE - node_id_size
        self._prev = Scru64Id.from_parts(0, node_id << self._counter_size)
        self._lock = threading.Lock()

    @classmethod
    def parse(cls, node_spec: str) -> Scru64Generator:
        """
        Creates a generator by parsing a node spec string that describes the node
        configuration.

        A node spec string consists of `node_id` and `node_id_size` separated by a slash
        (e.g., `"42/8"`, `"12345/16"`).
        """
        m = re.fullmatch(r"([0-9]+)/([0-9]+)", node_spec)
        if m is None:
            raise ValueError("invalid `node_spec`; it looks like: `42/8`, `12345/16`")
        return cls(int(m[1], 10), int(m[2], 10))

    def node_id(self) -> int:
        """Returns the `node_id` of the generator."""
        return self._prev.node_ctr >> self._counter_size

    def node_id_size(self) -> int:
        """Returns the size in bits of the `node_id` adopted by the generator."""
        return NODE_CTR_SIZE - self._counter_size

    def _init_node_ctr(self) -> int:
        """
        Calculates the combined `node_ctr` field value for the next `timestamp` tick.
        """
        # initialize counter at `counter_size - 1`-bit random number
        OVERFLOW_GUARD_SIZE = 1
        counter = 0
        if self._counter_size > OVERFLOW_GUARD_SIZE:
            counter = random.getrandbits(self._counter_size - OVERFLOW_GUARD_SIZE)

        return (self.node_id() << self._counter_size) | counter

    def generate(self) -> Scru64Id:
        """
        Generates a new SCRU64 ID object from the current `timestamp`.

        See the Scru64Generator class documentation for the description.
        """
        with self._lock:
            timestamp = datetime.datetime.now().timestamp()
            return self.generate_core(int(timestamp * 1_000))

    def generate_no_rewind(self) -> typing.Optional[Scru64Id]:
        """
        Generates a new SCRU64 ID object from the current `timestamp`, guaranteeing the
        monotonic order of generated IDs despite a significant timestamp rollback.

        See the Scru64Generator class documentation for the description.
        """
        with self._lock:
            timestamp = datetime.datetime.now().timestamp()
            return self.generate_core_no_rewind(int(timestamp * 1_000))

    def generate_or_wait(self) -> Scru64Id:
        """
        Returns a new SCRU64 ID object, or waits for one if not immediately available.

        See the Scru64Generator class documentation for the description.
        """
        DELAY = 64.0 / 1000.0
        while True:
            value = self.generate_no_rewind()
            if value is not None:
                return value
            else:
                time.sleep(DELAY)

    async def generate_or_wait_async(self) -> Scru64Id:
        """
        Returns a new SCRU64 ID object, or waits for one if not immediately available.

        See the Scru64Generator class documentation for the description.
        """
        DELAY = 64.0 / 1000.0
        while True:
            value = self.generate_no_rewind()
            if value is not None:
                return value
            else:
                await asyncio.sleep(DELAY)

    def generate_core(self, unix_ts_ms: int) -> Scru64Id:
        """
        Generates a new SCRU64 ID object from a Unix timestamp in milliseconds.

        See the Scru64Generator class documentation for the description.

        Unlike `generate()`, this method is NOT thread-safe. The generator object should
        be protected from concurrent accesses using a mutex or other synchronization
        mechanism to avoid race conditions.
        """
        value = self.generate_core_no_rewind(unix_ts_ms)
        if value is not None:
            return value
        else:
            # reset state and resume
            self._prev = Scru64Id.from_parts(unix_ts_ms >> 8, self._init_node_ctr())
            return self._prev

    def generate_core_no_rewind(self, unix_ts_ms: int) -> typing.Optional[Scru64Id]:
        """
        Generates a new SCRU64 ID object from a Unix timestamp in milliseconds,
        guaranteeing the monotonic order of generated IDs despite a significant
        timestamp rollback.

        See the Scru64Generator class documentation for the description.

        Unlike `generate_no_rewind()`, this method is NOT thread-safe. The generator
        object should be protected from concurrent accesses using a mutex or other
        synchronization mechanism to avoid race conditions.
        """
        ROLLBACK_ALLOWANCE = 40  # x256 milliseconds = ~10 seconds

        timestamp = unix_ts_ms >> 8
        if timestamp <= 0:
            raise ValueError("`timestamp` out of range")

        prev_timestamp = self._prev.timestamp
        if timestamp > prev_timestamp:
            self._prev = Scru64Id.from_parts(timestamp, self._init_node_ctr())
        elif timestamp + ROLLBACK_ALLOWANCE > prev_timestamp:
            # go on with previous timestamp if new one is not much smaller
            prev_node_ctr = self._prev.node_ctr
            counter_mask = (1 << self._counter_size) - 1
            if (prev_node_ctr & counter_mask) < counter_mask:
                self._prev = Scru64Id.from_parts(prev_timestamp, prev_node_ctr + 1)
            else:
                # increment timestamp at counter overflow
                self._prev = Scru64Id.from_parts(
                    prev_timestamp + 1, self._init_node_ctr()
                )
        else:
            # abort if clock moves back to unbearable extent
            return None
        return self._prev


global_generator: typing.Optional[Scru64Generator] = None


def get_global_generator() -> Scru64Generator:
    global global_generator
    if global_generator is None:
        node_spec = os.environ.get("SCRU64_NODE_SPEC")
        if node_spec is None:
            raise KeyError(
                "scru64: could not read config from SCRU64_NODE_SPEC env var"
            )
        global_generator = Scru64Generator.parse(node_spec)
    return global_generator


def new() -> Scru64Id:
    """
    Generates a new SCRU64 ID object using the global generator.
    """
    return get_global_generator().generate_or_wait()


def new_string() -> str:
    """
    Generates a new SCRU64 ID encoded in the 12-digit canonical string representation
    using the global generator.
    """
    return str(new())


async def new_async() -> Scru64Id:
    """
    Generates a new SCRU64 ID object using the global generator.
    """
    return await get_global_generator().generate_or_wait_async()


async def new_string_async() -> str:
    """
    Generates a new SCRU64 ID encoded in the 12-digit canonical string representation
    using the global generator.
    """
    return str(await get_global_generator().generate_or_wait_async())
