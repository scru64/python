"""SCRU64: Sortable, Clock-based, Realm-specifically Unique identifier"""

from __future__ import annotations

__all__ = [
    "new",
    "new_string",
    "new_sync",
    "new_string_sync",
    "Scru64Id",
    "Scru64Generator",
    "GlobalGenerator",
    "NodeSpec",
    "counter_mode",
]

import asyncio
import datetime
import os
import re
import threading
import time
import typing

from .counter_mode import CounterMode, RenewContext, DefaultCounterMode

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
        """
        Creates an object from a 64-bit integer.

        Raises:
            `ValueError` if the argument is out of the valid value range.
        """
        self._value = int_value
        if not (0 <= int_value <= MAX_SCRU64_INT):
            raise ValueError("out of valid integer range")

    def __int__(self) -> int:
        """Returns the integer representation."""
        return self._value

    @classmethod
    def from_str(cls, str_value: str) -> Scru64Id:
        """
        Creates an object from a 12-digit string representation.

        Raises:
            `ValueError` if the argument is not a valid string representation.
        """
        if re.fullmatch(r"[0-9A-Za-z]{12}", str_value, flags=re.ASCII) is None:
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

        Raises:
            `ValueError` if any argument is out of the valid value range.
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
        node_spec: typing.Union[str, NodeSpec],
        *,
        counter_mode: typing.Optional[CounterMode] = None,
    ) -> None:
        """
        Creates a new generator with the given node configuration and counter
        initialization mode.

        The `node_spec` may be passed as a string or as a `NodeSpec` instance. See
        `NodeSpec` for the node spec string format.

        Raises:
            `ValueError` if the `node_spec` is given in a string and could not be parsed
            as a well-formed node spec string.
        """
        if isinstance(node_spec, str):
            node_spec = NodeSpec.parse(node_spec)

        self._prev = node_spec._node_prev
        self._counter_size = NODE_CTR_SIZE - node_spec.node_id_size()

        if counter_mode is not None:
            self._counter_mode = counter_mode
        else:
            # reserve one overflow guard bit if `counter_size` is four or less
            if self._counter_size <= 4:
                self._counter_mode = DefaultCounterMode(1)
            else:
                self._counter_mode = DefaultCounterMode(0)

        self._lock = threading.Lock()

    def node_id(self) -> int:
        """Returns the `node_id` of the generator."""
        return self._prev.node_ctr >> self._counter_size

    def node_id_size(self) -> int:
        """Returns the size in bits of the `node_id` adopted by the generator."""
        return NODE_CTR_SIZE - self._counter_size

    def node_spec(self) -> NodeSpec:
        """Returns the node configuration specifier describing the generator state."""
        return NodeSpec(self._prev, self.node_id_size())

    def _renew_node_ctr(self, timestamp: int) -> int:
        """
        Calculates the combined `node_ctr` field value for the next `timestamp` tick.
        """
        node_id = self.node_id()
        context = RenewContext(timestamp=timestamp, node_id=node_id)
        counter = self._counter_mode.renew(self._counter_size, context)
        if counter >= (1 << self._counter_size):
            raise AssertionError("illegal `CounterMode` implementation")

        return (node_id << self._counter_size) | counter

    def generate(self) -> typing.Optional[Scru64Id]:
        """
        Generates a new SCRU64 ID object from the current `timestamp`, or returns `None`
        upon significant timestamp rollback.

        See the `Scru64Generator` class documentation for the description.
        """
        with self._lock:
            timestamp = datetime.datetime.now().timestamp()
            return self.generate_or_abort_core(int(timestamp * 1_000), 10_000)

    def generate_or_reset(self) -> Scru64Id:
        """
        Generates a new SCRU64 ID object from the current `timestamp`, or resets the
        generator upon significant timestamp rollback.

        See the `Scru64Generator` class documentation for the description.
        """
        with self._lock:
            timestamp = datetime.datetime.now().timestamp()
            return self.generate_or_reset_core(int(timestamp * 1_000), 10_000)

    def generate_or_sleep(self) -> Scru64Id:
        """
        Returns a new SCRU64 ID object, or synchronously sleeps and waits for one if not
        immediately available.

        See the `Scru64Generator` class documentation for the description.
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

        See the `Scru64Generator` class documentation for the description.
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

        See the `Scru64Generator` class documentation for the description.

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

        See the `Scru64Generator` class documentation for the description.

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


class NodeSpec:
    """
    Represents a node configuration specifier used to build a `Scru64Generator`.

    A `NodeSpec` is usually expressed as a node spec string, which starts with a decimal
    `node_id`, a hexadecimal `node_id` prefixed with `"0x"`, or a 12-digit `node_prev`
    SCRU64 ID value, followed by a slash and a decimal `node_id_size` value ranging from
    1 to 23 (e.g., `"42/8"`, `"0xb00/12"`, `"0u2r85hm2pt3/16"`). The first and second
    forms create a fresh new generator with the given `node_id`, while the third form
    constructs one that generates subsequent SCRU64 IDs to the `node_prev`.
    """

    def __init__(
        self, node_id_or_prev: typing.Union[int, Scru64Id], node_id_size: int
    ) -> None:
        """
        Creates an instance with `node_id` or `node_prev` and `node_id_size` values.

        Raises:
            `ValueError` if the `node_id_size` is less than 1 or greater than 23 or if
            the `node_id` does not fit in `node_id_size` bits.
        """
        if node_id_size <= 0 or node_id_size >= NODE_CTR_SIZE:
            raise ValueError(f"`node_id_size` ({node_id_size}) must range from 1 to 23")
        if not isinstance(node_id_or_prev, Scru64Id):
            if node_id_or_prev < 0 or node_id_or_prev >= (1 << node_id_size):
                raise ValueError(
                    f"`node_id` ({node_id_or_prev}) must fit in `node_id_size` ({node_id_size}) bits"
                )
            counter_size = NODE_CTR_SIZE - node_id_size
            node_id_or_prev = Scru64Id.from_parts(0, node_id_or_prev << counter_size)
        self._node_prev: Scru64Id = node_id_or_prev
        self._node_id_size: int = node_id_size

    def node_id_size(self) -> int:
        """Returns the `node_id_size` value."""
        return self._node_id_size

    def node_id(self) -> int:
        """
        Returns the `node_id` value given at instance creation or encoded in the
        `node_prev` value.
        """
        counter_size = NODE_CTR_SIZE - self._node_id_size
        return self._node_prev.node_ctr >> counter_size

    def node_prev(self) -> typing.Optional[Scru64Id]:
        """
        Returns the `node_prev` value if `self` is constructed with one or `None`
        otherwise.
        """
        if self._node_prev.timestamp > 0:
            return self._node_prev
        else:
            return None

    @classmethod
    def parse(cls, node_spec: str) -> NodeSpec:
        """
        Creates an instance from a node spec string.

        Raises:
            `ValueError` if an invalid `node_spec` string is passed.
        """
        m = re.fullmatch(
            r"(?:([0-9a-z]{12})|([0-9]{1,8})|0x([0-9a-f]{1,6}))\/([0-9]{1,3})",
            node_spec,
            flags=re.ASCII | re.IGNORECASE,
        )
        if m is None:
            raise ValueError(
                'could not parse string as node spec (expected: e.g., "42/8", "0xb00/12", "0u2r85hm2pt3/16")'
            )
        node_id_size = int(m[4], 10)
        if m[1] is not None:
            return cls(Scru64Id.from_str(m[1]), node_id_size)
        elif m[2] is not None:
            return cls(int(m[2], 10), node_id_size)
        elif m[3] is not None:
            return cls(int(m[3], 16), node_id_size)
        else:
            raise AssertionError("unreachable")

    def __str__(self) -> str:
        node_prev = self.node_prev()
        if node_prev is not None:
            return f"{node_prev}/{self._node_id_size}"
        else:
            return f"{self.node_id()}/{self._node_id_size}"


class GlobalGenerator:
    """
    The gateway class that forwards supported method calls to the process-wide global
    generator.

    The global generator reads the node configuration from the `SCRU64_NODE_SPEC`
    environment variable by default, and it raises an error if it fails to read a
    well-formed node spec string (e.g., `"42/8"`, `"0xb00/12"`, `"0u2r85hm2pt3/16"`)
    when a generator method is first called. See also `NodeSpec` for the node spec
    string format.
    """

    _instance: typing.Optional[Scru64Generator] = None

    @classmethod
    def _get(cls) -> Scru64Generator:
        if cls._instance is None:
            node_spec = os.environ.get("SCRU64_NODE_SPEC")
            if node_spec is None:
                raise KeyError(
                    "scru64: could not read config from SCRU64_NODE_SPEC env var"
                )
            cls._instance = Scru64Generator(node_spec)
        return cls._instance

    @classmethod
    def initialize(cls, node_spec: typing.Union[str, NodeSpec]) -> bool:
        """
        Initializes the global generator, if not initialized, with the node spec passed.

        This method tries to configure the global generator with the argument only when
        the global generator is not yet initialized. Otherwise, it preserves the
        existing configuration.

        Raises:
            `ValueError` if the `node_spec` is given in a string and could not be parsed
            as a well-formed node spec string.
        Returns:
            `True` if this method configures the global generator or `False` if it
            preserves the existing configuration.
        """
        if cls._instance is None:
            cls._instance = Scru64Generator(node_spec)
            return True
        else:
            return False

    @classmethod
    def generate(cls) -> typing.Optional[Scru64Id]:
        """Calls `Scru64Generator.generate` of the global generator."""
        return cls._get().generate()

    @classmethod
    def generate_or_sleep(cls) -> Scru64Id:
        """Calls `Scru64Generator.generate_or_sleep` of the global generator."""
        return cls._get().generate_or_sleep()

    @classmethod
    async def generate_or_await(cls) -> Scru64Id:
        """Calls `Scru64Generator.generate_or_await` of the global generator."""
        return await cls._get().generate_or_await()

    @classmethod
    def node_id(cls) -> int:
        """Calls `Scru64Generator.node_id` of the global generator."""
        return cls._get().node_id()

    @classmethod
    def node_id_size(cls) -> int:
        """Calls `Scru64Generator.node_id_size` of the global generator."""
        return cls._get().node_id_size()

    @classmethod
    def node_spec(cls) -> NodeSpec:
        """Calls `Scru64Generator.node_spec` of the global generator."""
        return cls._get().node_spec()


def new_sync() -> Scru64Id:
    """
    Generates a new SCRU64 ID object using the global generator.

    The `GlobalGenerator` reads the node configuration from the `SCRU64_NODE_SPEC`
    environment variable by default, and it raises an error if it fails to read a
    well-formed node spec string (e.g., `"42/8"`, `"0xb00/12"`, `"0u2r85hm2pt3/16"`)
    when a generator method is first called. See also `NodeSpec` for the node spec
    string format.

    This function usually returns a value immediately, but if not possible, it sleeps
    and waits for the next timestamp tick. It employs blocking sleep to wait; see
    `new` for the non-blocking equivalent.

    Raises:
        An error if the global generator is not properly configured.
    """
    return GlobalGenerator.generate_or_sleep()


def new_string_sync() -> str:
    """
    Generates a new SCRU64 ID encoded in the 12-digit canonical string representation
    using the global generator.

    The `GlobalGenerator` reads the node configuration from the `SCRU64_NODE_SPEC`
    environment variable by default, and it raises an error if it fails to read a
    well-formed node spec string (e.g., `"42/8"`, `"0xb00/12"`, `"0u2r85hm2pt3/16"`)
    when a generator method is first called. See also `NodeSpec` for the node spec
    string format.

    This function usually returns a value immediately, but if not possible, it sleeps
    and waits for the next timestamp tick. It employs blocking sleep to wait; see
    `new_string` for the non-blocking equivalent.

    Raises:
        An error if the global generator is not properly configured.
    """
    return str(new_sync())


async def new() -> Scru64Id:
    """
    Generates a new SCRU64 ID object using the global generator.

    The `GlobalGenerator` reads the node configuration from the `SCRU64_NODE_SPEC`
    environment variable by default, and it raises an error if it fails to read a
    well-formed node spec string (e.g., `"42/8"`, `"0xb00/12"`, `"0u2r85hm2pt3/16"`)
    when a generator method is first called. See also `NodeSpec` for the node spec
    string format.

    This function usually returns a value immediately, but if not possible, it sleeps
    and waits for the next timestamp tick.

    Raises:
        An error if the global generator is not properly configured.
    """
    return await GlobalGenerator.generate_or_await()


async def new_string() -> str:
    """
    Generates a new SCRU64 ID encoded in the 12-digit canonical string representation
    using the global generator.

    The `GlobalGenerator` reads the node configuration from the `SCRU64_NODE_SPEC`
    environment variable by default, and it raises an error if it fails to read a
    well-formed node spec string (e.g., `"42/8"`, `"0xb00/12"`, `"0u2r85hm2pt3/16"`)
    when a generator method is first called. See also `NodeSpec` for the node spec
    string format.

    This function usually returns a value immediately, but if not possible, it sleeps
    and waits for the next timestamp tick.

    Raises:
        An error if the global generator is not properly configured.
    """
    return str(await GlobalGenerator.generate_or_await())
