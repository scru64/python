from __future__ import annotations

import datetime
import unittest

from scru64 import NodeSpec, Scru64Generator, Scru64Id

from . import EXAMPLE_NODE_SPECS


class TestGenerator(unittest.TestCase):
    def _assert_consecutive(self, first: Scru64Id, second: Scru64Id) -> None:
        self.assertLess(first, second)
        if first.timestamp == second.timestamp:
            self.assertEqual(first.node_ctr + 1, second.node_ctr)
        else:
            self.assertEqual(first.timestamp + 1, second.timestamp)

    def test_generate_or_reset(self) -> None:
        """
        Normally generates monotonic IDs or resets state upon significant rollback.
        """
        N_LOOPS = 64
        ALLOWANCE = 10_000

        for e in EXAMPLE_NODE_SPECS:
            counter_size = 24 - e.node_id_size
            g = Scru64Generator(NodeSpec(e.node_id, e.node_id_size))

            # happy path
            ts = 1_577_836_800_000  # 2020-01-01
            prev = g.generate_or_reset_core(ts, ALLOWANCE)
            for _ in range(N_LOOPS):
                ts += 16
                curr = g.generate_or_reset_core(ts, ALLOWANCE)
                self._assert_consecutive(prev, curr)
                self.assertLess(curr.timestamp - (ts >> 8), ALLOWANCE >> 8)
                self.assertEqual(curr.node_ctr >> counter_size, e.node_id)

                prev = curr

            # keep monotonic order under mildly decreasing timestamps
            ts += ALLOWANCE * 16
            prev = g.generate_or_reset_core(ts, ALLOWANCE)
            for _ in range(N_LOOPS):
                ts -= 16
                curr = g.generate_or_reset_core(ts, ALLOWANCE)
                self._assert_consecutive(prev, curr)
                self.assertLess(curr.timestamp - (ts >> 8), ALLOWANCE >> 8)
                self.assertEqual(curr.node_ctr >> counter_size, e.node_id)

                prev = curr

            # reset state with significantly decreasing timestamps
            ts += ALLOWANCE * 16
            prev = g.generate_or_reset_core(ts, ALLOWANCE)
            for _ in range(N_LOOPS):
                ts -= ALLOWANCE + 0x100
                curr = g.generate_or_reset_core(ts, ALLOWANCE)
                self.assertGreater(prev, curr)
                self.assertLess(curr.timestamp - (ts >> 8), ALLOWANCE >> 8)
                self.assertEqual(curr.node_ctr >> counter_size, e.node_id)

                prev = curr

    def test_generate_or_abort(self) -> None:
        """Normally generates monotonic IDs or aborts upon significant rollback."""
        N_LOOPS = 64
        ALLOWANCE = 10_000

        for e in EXAMPLE_NODE_SPECS:
            counter_size = 24 - e.node_id_size
            g = Scru64Generator(NodeSpec(e.node_id, e.node_id_size))

            # happy path
            ts = 1_577_836_800_000  # 2020-01-01
            prev = g.generate_or_abort_core(ts, ALLOWANCE)
            assert prev is not None
            for _ in range(N_LOOPS):
                ts += 16
                curr = g.generate_or_abort_core(ts, ALLOWANCE)
                assert curr is not None
                self._assert_consecutive(prev, curr)
                self.assertLess(curr.timestamp - (ts >> 8), ALLOWANCE >> 8)
                self.assertEqual(curr.node_ctr >> counter_size, e.node_id)

                prev = curr

            # keep monotonic order under mildly decreasing timestamps
            ts += ALLOWANCE * 16
            prev = g.generate_or_abort_core(ts, ALLOWANCE)
            assert prev is not None
            for _ in range(N_LOOPS):
                ts -= 16
                curr = g.generate_or_abort_core(ts, ALLOWANCE)
                assert curr is not None
                self._assert_consecutive(prev, curr)
                self.assertLess(curr.timestamp - (ts >> 8), ALLOWANCE >> 8)
                self.assertEqual(curr.node_ctr >> counter_size, e.node_id)

                prev = curr

            # abort with significantly decreasing timestamps
            ts += ALLOWANCE * 16
            g.generate_or_abort_core(ts, ALLOWANCE)
            ts -= ALLOWANCE + 0x100
            for _ in range(N_LOOPS):
                ts -= 16
                self.assertIsNone(g.generate_or_abort_core(ts, ALLOWANCE))


class TestGeneratorAsync(unittest.IsolatedAsyncioTestCase):
    def now(self) -> int:
        return int(datetime.datetime.now().timestamp() * 1_000) >> 8

    async def test_clock_integration(self) -> None:
        """Embeds up-to-date timestamp."""
        for e in EXAMPLE_NODE_SPECS:
            g = Scru64Generator(NodeSpec(e.node_id, e.node_id_size))
            ts_now = self.now()
            x = g.generate()
            assert x is not None
            self.assertLessEqual(x.timestamp - ts_now, 1)

            ts_now = self.now()
            x = g.generate_or_reset()
            self.assertLessEqual(x.timestamp - ts_now, 1)

            ts_now = self.now()
            x = g.generate_or_sleep()
            self.assertLessEqual(x.timestamp - ts_now, 1)

            ts_now = self.now()
            x = await g.generate_or_await()
            self.assertLessEqual(x.timestamp - ts_now, 1)
