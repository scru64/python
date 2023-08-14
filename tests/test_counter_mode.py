from __future__ import annotations

import math
import unittest

from scru64.counter_mode import DefaultCounterMode, RenewContext


class TestCounterMode(unittest.TestCase):
    def test_that_may_fail_at_low_probability(self) -> None:
        """
        `DefaultCounterMode` returns random numbers, setting the leading guard bits to
        zero.

        This case includes statistical tests for the random number generator and thus
        may fail at a certain low probability.
        """

        N = 256

        # set margin based on binom dist 99.999999% confidence interval
        margin = 5.730729 * math.sqrt(0.5 * 0.5 / N)

        context = RenewContext(timestamp=0x0123_4567_89AB, node_id=0)
        for counter_size in range(1, 24):
            for overflow_guard_size in range(24):
                # count number of set bits by bit position (from LSB to MSB)
                counts_by_pos = [0] * 24

                c = DefaultCounterMode(overflow_guard_size)
                for _ in range(N):
                    n = c.renew(counter_size, context)
                    for i in range(24):
                        counts_by_pos[i] += n & 1
                        n >>= 1

                filled = max(0, counter_size - overflow_guard_size)
                for e in counts_by_pos[:filled]:
                    self.assertLess(abs(e / N - 0.5), margin)
                for e in counts_by_pos[filled:]:
                    self.assertEqual(e, 0)
