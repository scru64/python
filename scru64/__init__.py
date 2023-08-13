"""SCRU64: Sortable, Clock-based, Realm-specifically Unique identifier"""

from __future__ import annotations

__all__ = [
    "new",
    "new_string",
    "new_sync",
    "new_string_sync",
    "Scru64Id",
    "Scru64Generator",
    "CounterMode",
    "RenewContext",
    "DefaultCounterMode",
]

import asyncio
import datetime
import os
import random
import re
import threading
import time
import typing
from dataclasses import dataclass

# The maximum valid value (i.e., `zzzzzzzzzzzz`).
MAX_SCRU64_INT = 36**12 - 1

# The total size in bits of the `node_id` and `counter` fields.
NODE_CTR_SIZE = 24

# The maximum valid value of the `timestamp` field.
MAX_TIMESTAMP = MAX_SCRU64_INT >> NODE_CTR_SIZE

# The maximum valid value of the combined `node_ctr` field.
MAX_NODE_CTR = (1 << NODE_CTR_SIZE) - 1

# Digit characters used in the Base36 notation.
DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"


class Scru64Id:
    """Represents a SCRU64 ID."""

    __slots__ = "_value"

    def __init__(self, int_value: int) -> None:
        """Creates an object from a 64-bit integer."""
        self._value = int_value
        if not (0 <= int_value <= MAX_SCRU64_INT):
            raise ValueError("out of valid integer range")

    def __int__(self) -> int:
        """Returns the integer representation."""
        return self._value

    @classmethod
    def from_str(cls, str_value: str) -> Scru64Id:
        """Creates an object from a 12-digit string representation."""
        if re.fullmatch(r"[0-9A-Za-z]{12}", str_value) is None:
            raise ValueError("invalid string representation")
        return cls(int(str_value, 36))

    def __str__(self) -> str:
        """Returns the 12-digit canonical string representation."""
        buffer = ["0"] * 12
        n = self._value
        for i in range(12):
            (n, rem) = divmod(n, 36)
            buffer[11 - i] = DIGITS[rem]
        return "".join(buffer)

    @classmethod
    def from_parts(cls, timestamp: int, node_ctr: int) -> Scru64Id:
        """
        Creates a value from the `timestamp` and the combined `node_ctr` field value.
        """
        if timestamp < 0 or timestamp > MAX_TIMESTAMP:
            raise ValueError("`timestamp` out of range")
        if node_ctr < 0 or node_ctr > MAX_NODE_CTR:
            raise ValueError("`node_ctr` out of range")
        return cls(timestamp << NODE_CTR_SIZE | node_ctr)

    @property
    def timestamp(self) -> int:
        """Returns the `timestamp` field value."""
        return self._value >> NODE_CTR_SIZE

    @property
    def node_ctr(self) -> int:
        """
        Returns the `node_id` and `counter` field values combined as a single integer.
        """
        return self._value & MAX_NODE_CTR

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

    | Flavor                 | Timestamp | Thread- | On big clock rewind |
    | ---------------------- | --------- | ------- | ------------------- |
    | generate               | Now       | Safe    | Returns `None`      |
    | generate_or_reset      | Now       | Safe    | Resets generator    |
    | generate_or_sleep      | Now       | Safe    | Sleeps (blocking)   |
    | generate_or_await      | Now       | Safe    | Sleeps (async)      |
    | generate_or_abort_core | Argument  | Unsafe  | Returns `None`      |
    | generate_or_reset_core | Argument  | Unsafe  | Resets generator    |

    All of these methods return monotonically increasing IDs unless a timestamp provided
    is significantly (by default, approx. 10 seconds) smaller than the one embedded in
    the immediately preceding ID. If such a significant clock rollback is detected, (1)
    the `generate` (or_abort) method aborts and returns `None`; (2) the `or_reset`
    variants reset the generator and return a new ID based on the given timestamp; and,
    (3) the `or_sleep` and `or_await` methods sleep and wait for the next timestamp
    tick. The `core` functions offer low-level thread-unsafe primitives.
    """

    def __init__(
        self,
        node_id: int,
        node_id_size: int,
        *,
        counter_mode: typing.Optional[CounterMode] = None,
    ) -> None:
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

        if counter_mode is not None:
            self._counter_mode = counter_mode
        else:
            # reserve one overflow guard bit if `counter_size` is four or less
            if self._counter_size <= 4:
                self._counter_mode = DefaultCounterMode(1)
            else:
                self._counter_mode = DefaultCounterMode(0)

    @classmethod
    def parse(cls, node_spec: str) -> Scru64Generator:
        """
        Creates a generator by parsing a node spec string that describes the node
        configuration.

        A node spec string consists of `node_id` and `node_id_size` separated by a slash
        (e.g., `"42/8"`, `"12345/16"`).
        """
        m = re.fullmatch(r"([0-9]{1,10})/([0-9]{1,3})", node_spec)
        if m is None:
            raise ValueError("invalid `node_spec`; it looks like: `42/8`, `12345/16`")
        return cls(int(m[1], 10), int(m[2], 10))

    def node_id(self) -> int:
        """Returns the `node_id` of the generator."""
        return self._prev.node_ctr >> self._counter_size

    def node_id_size(self) -> int:
        """Returns the size in bits of the `node_id` adopted by the generator."""
        return NODE_CTR_SIZE - self._counter_size

    def _renew_node_ctr(self, timestamp: int) -> int:
        """
        Calculates the combined `node_ctr` field value for the next `timestamp` tick.
        """
        node_id = self.node_id()
        context = RenewContext(timestamp=timestamp, node_id=node_id)
        counter = self._counter_mode.renew(self._counter_size, context)
        if counter >= (1 << self._counter_size):
            raise RuntimeError("illegal `CounterMode` implementation")

        return (node_id << self._counter_size) | counter

    def generate(self) -> typing.Optional[Scru64Id]:
        """
        Generates a new SCRU64 ID object from the current `timestamp`, or returns `None`
        upon significant timestamp rollback.

        See the Scru64Generator class documentation for the description.
        """
        with self._lock:
            timestamp = datetime.datetime.now().timestamp()
            return self.generate_or_abort_core(int(timestamp * 1_000), 10_000)

    def generate_or_reset(self) -> Scru64Id:
        """
        Generates a new SCRU64 ID object from the current `timestamp`, or resets the
        generator upon significant timestamp rollback.

        See the Scru64Generator class documentation for the description.
        """
        with self._lock:
            timestamp = datetime.datetime.now().timestamp()
            return self.generate_or_reset_core(int(timestamp * 1_000), 10_000)

    def generate_or_sleep(self) -> Scru64Id:
        """
        Returns a new SCRU64 ID object, or synchronously sleeps and waits for one if not
        immediately available.

        See the Scru64Generator class documentation for the description.
        """
        DELAY = 64.0 / 1000.0
        while True:
            value = self.generate()
            if value is not None:
                return value
            else:
                time.sleep(DELAY)

    async def generate_or_await(self) -> Scru64Id:
        """
        Returns a new SCRU64 ID object, or asynchronously sleeps and waits for one if
        not immediately available.

        See the Scru64Generator class documentation for the description.
        """
        DELAY = 64.0 / 1000.0
        while True:
            value = self.generate()
            if value is not None:
                return value
            else:
                await asyncio.sleep(DELAY)

    def generate_or_reset_core(
        self, unix_ts_ms: int, rollback_allowance: int
    ) -> Scru64Id:
        """
        Generates a new SCRU64 ID object from a Unix timestamp in milliseconds, or
        resets the generator upon significant timestamp rollback.

        See the Scru64Generator class documentation for the description.

        The `rollback_allowance` parameter specifies the amount of `unix_ts_ms` rollback
        that is considered significant. A suggested value is `10_000` (milliseconds).

        Unlike `generate_or_reset()`, this method is NOT thread-safe. The generator
        object should be protected from concurrent accesses using a mutex or other
        synchronization mechanism to avoid race conditions.
        """
        value = self.generate_or_abort_core(unix_ts_ms, rollback_allowance)
        if value is not None:
            return value
        else:
            # reset state and resume
            timestamp = unix_ts_ms >> 8
            self._prev = Scru64Id.from_parts(timestamp, self._renew_node_ctr(timestamp))
            return self._prev

    def generate_or_abort_core(
        self, unix_ts_ms: int, rollback_allowance: int
    ) -> typing.Optional[Scru64Id]:
        """
        Generates a new SCRU64 ID object from a Unix timestamp in milliseconds, or
        returns `None` upon significant timestamp rollback.

        See the Scru64Generator class documentation for the description.

        The `rollback_allowance` parameter specifies the amount of `unix_ts_ms` rollback
        that is considered significant. A suggested value is `10_000` (milliseconds).

        Unlike `generate()`, this method is NOT thread-safe. The generator object should
        be protected from concurrent accesses using a mutex or other synchronization
        mechanism to avoid race conditions.
        """
        timestamp = unix_ts_ms >> 8
        allowance = rollback_allowance >> 8
        if timestamp <= 0:
            raise ValueError("`timestamp` out of range")
        elif allowance < 0 or allowance >= (1 << 40):
            raise ValueError("`rollback_allowance` out of reasonable range")

        prev_timestamp = self._prev.timestamp
        if timestamp > prev_timestamp:
            self._prev = Scru64Id.from_parts(timestamp, self._renew_node_ctr(timestamp))
        elif timestamp + allowance >= prev_timestamp:
            # go on with previous timestamp if new one is not much smaller
            prev_node_ctr = self._prev.node_ctr
            counter_mask = (1 << self._counter_size) - 1
            if (prev_node_ctr & counter_mask) < counter_mask:
                self._prev = Scru64Id.from_parts(prev_timestamp, prev_node_ctr + 1)
            else:
                # increment timestamp at counter overflow
                self._prev = Scru64Id.from_parts(
                    prev_timestamp + 1, self._renew_node_ctr(prev_timestamp + 1)
                )
        else:
            # abort if clock went backwards to unbearable extent
            return None
        return self._prev


class CounterMode(typing.Protocol):
    """
    A protocol to customize the initial counter value for each new `timestamp`.

    `Scru64Generator` calls `renew()` to obtain the initial counter value when the
    `timestamp` field has changed since the immediately preceding ID. Types implementing
    this protocol may apply their respective logic to calculate the initial counter
    value.
    """

    def renew(self, counter_size: int, context: RenewContext) -> int:
        """
        Returns the next initial counter value of `counter_size` bits.

        `Scru64Generator` passes the `counter_size` (from 1 to 23) and other context
        information that may be useful for counter renewal. The returned value must be
        within the range of `counter_size`-bit unsigned integer.
        """


@dataclass
class RenewContext:
    """
    Represents the context information provided by `Scru64Generator` to
    `CounterMode.renew()`.
    """

    timestamp: int
    node_id: int


class DefaultCounterMode:
    """
    The default "initialize a portion counter" strategy.

    With this strategy, the counter is reset to a random number for each new `timestamp`
    tick, but some specified leading bits are set to zero to reserve space as the
    counter overflow guard.

    Note that the random number generator employed is not cryptographically strong. This
    mode does not pay for security because a small random number is insecure anyway.
    """

    def __init__(self, overflow_guard_size: int) -> None:
        """Creates a new instance with the size (in bits) of overflow guard bits."""
        if overflow_guard_size < 0:
            raise ValueError("`overflow_guard_size` must be an unsigned integer")
        self._overflow_guard_size = overflow_guard_size

    def renew(self, counter_size: int, context: RenewContext) -> int:
        """Returns the next initial counter value of `counter_size` bits."""
        if counter_size > self._overflow_guard_size:
            return random.getrandbits(counter_size - self._overflow_guard_size)
        else:
            return 0


global_gen: typing.Optional[Scru64Generator] = None


def get_global_generator() -> Scru64Generator:
    global global_gen
    if global_gen is None:
        node_spec = os.environ.get("SCRU64_NODE_SPEC")
        if node_spec is None:
            raise KeyError(
                "scru64: could not read config from SCRU64_NODE_SPEC env var"
            )
        global_gen = Scru64Generator.parse(node_spec)
    return global_gen


def new_sync() -> Scru64Id:
    """
    Generates a new SCRU64 ID object using the global generator.

    The global generator reads the node configuration from the `SCRU64_NODE_SPEC`
    environment variable. A node spec string consists of `node_id` and `node_id_size`
    separated by a slash (e.g., `"42/8"`, `"12345/16"`).

    This function usually returns a value immediately, but if not possible, it sleeps
    and waits for the next timestamp tick. It employs blocking sleep to wait; see
    `new` for the non-blocking equivalent.

    Raises:
        Exception if the global generator is not properly configured through the
        environment variable.
    """
    return get_global_generator().generate_or_sleep()


def new_string_sync() -> str:
    """
    Generates a new SCRU64 ID encoded in the 12-digit canonical string representation
    using the global generator.

    The global generator reads the node configuration from the `SCRU64_NODE_SPEC`
    environment variable. A node spec string consists of `node_id` and `node_id_size`
    separated by a slash (e.g., `"42/8"`, `"12345/16"`).

    This function usually returns a value immediately, but if not possible, it sleeps
    and waits for the next timestamp tick. It employs blocking sleep to wait; see
    `new_string` for the non-blocking equivalent.

    Raises:
        Exception if the global generator is not properly configured through the
        environment variable.
    """
    return str(new_sync())


async def new() -> Scru64Id:
    """
    Generates a new SCRU64 ID object using the global generator.

    The global generator reads the node configuration from the `SCRU64_NODE_SPEC`
    environment variable. A node spec string consists of `node_id` and `node_id_size`
    separated by a slash (e.g., `"42/8"`, `"12345/16"`).

    This function usually returns a value immediately, but if not possible, it sleeps
    and waits for the next timestamp tick.

    Raises:
        Exception if the global generator is not properly configured through the
        environment variable.
    """
    return await get_global_generator().generate_or_await()


async def new_string() -> str:
    """
    Generates a new SCRU64 ID encoded in the 12-digit canonical string representation
    using the global generator.

    The global generator reads the node configuration from the `SCRU64_NODE_SPEC`
    environment variable. A node spec string consists of `node_id` and `node_id_size`
    separated by a slash (e.g., `"42/8"`, `"12345/16"`).

    This function usually returns a value immediately, but if not possible, it sleeps
    and waits for the next timestamp tick.

    Raises:
        Exception if the global generator is not properly configured through the
        environment variable.
    """
    return str(await get_global_generator().generate_or_await())
