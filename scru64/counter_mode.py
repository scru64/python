"""Types to customize the counter behavior of `Scru64Generator`."""

from __future__ import annotations

import dataclasses
import random
import typing


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


@dataclasses.dataclass(frozen=True)
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
