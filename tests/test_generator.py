from __future__ import annotations

import datetime
import unittest

from scru64 import Scru64Generator, Scru64Id


NODE_SPECS: list[tuple[int, int, str]] = [
    (0, 1, "0/1"),
    (1, 1, "1/1"),
    (0, 8, "0/8"),
    (42, 8, "42/8"),
    (255, 8, "255/8"),
    (0, 16, "0/16"),
    (334, 16, "334/16"),
    (65535, 16, "65535/16"),
    (0, 23, "0/23"),
    (123456, 23, "123456/23"),
    (8388607, 23, "8388607/23"),
]


class TestGenerator(unittest.TestCase):
    def test_constructor(self) -> None:
        """Initializes with node ID and size pair and node spec string."""
        for node_id, node_id_size, node_spec in NODE_SPECS:
            x = Scru64Generator(node_id, node_id_size)
            self.assertEqual(x.node_id(), node_id)
            self.assertEqual(x.node_id_size(), node_id_size)

            y = Scru64Generator.parse(node_spec)
            self.assertEqual(y.node_id(), node_id)
            self.assertEqual(y.node_id_size(), node_id_size)

    def test_constructor_error(self) -> None:
        """Fails to initialize with invalid node spec string."""
        cases = [
            "",
            " 42/8",
            "42/8 ",
            " 42/8 ",
            "42 / 8",
            "+42/8",
            "42/+8",
            "-42/8",
            "42/-8",
            "ab/8",
            "0x42/8",
            "0/0",
            "0/24",
            "8/1",
            "1024/8",
        ]

        for e in cases:
            with self.assertRaises(Exception):
                Scru64Generator.parse(e)

    def _test_consecutive_pair(self, first: Scru64Id, second: Scru64Id) -> None:
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

        for node_id, node_id_size, node_spec in NODE_SPECS:
            counter_size = 24 - node_id_size
            g = Scru64Generator.parse(node_spec)

            # happy path
            ts = 1_577_836_800_000  # 2020-01-01
            prev = g.generate_or_reset_core(ts, ALLOWANCE)
            for _ in range(N_LOOPS):
                ts += 16
                curr = g.generate_or_reset_core(ts, ALLOWANCE)
                self._test_consecutive_pair(prev, curr)
                self.assertLess(curr.timestamp - (ts >> 8), ALLOWANCE >> 8)
                self.assertEqual(curr.node_ctr >> counter_size, node_id)

                prev = curr

            # keep monotonic order under mildly decreasing timestamps
            ts += ALLOWANCE * 16
            prev = g.generate_or_reset_core(ts, ALLOWANCE)
            for _ in range(N_LOOPS):
                ts -= 16
                curr = g.generate_or_reset_core(ts, ALLOWANCE)
                self._test_consecutive_pair(prev, curr)
                self.assertLess(curr.timestamp - (ts >> 8), ALLOWANCE >> 8)
                self.assertEqual(curr.node_ctr >> counter_size, node_id)

                prev = curr

            # reset state with significantly decreasing timestamps
            ts += ALLOWANCE * 16
            prev = g.generate_or_reset_core(ts, ALLOWANCE)
            for _ in range(N_LOOPS):
                ts -= ALLOWANCE
                curr = g.generate_or_reset_core(ts, ALLOWANCE)
                self.assertGreater(prev, curr)
                self.assertLess(curr.timestamp - (ts >> 8), ALLOWANCE >> 8)
                self.assertEqual(curr.node_ctr >> counter_size, node_id)

                prev = curr

    def test_generate_or_abort(self) -> None:
        """Normally generates monotonic IDs or aborts upon significant rollback."""
        N_LOOPS = 64
        ALLOWANCE = 10_000

        for node_id, node_id_size, node_spec in NODE_SPECS:
            counter_size = 24 - node_id_size
            g = Scru64Generator.parse(node_spec)

            # happy path
            ts = 1_577_836_800_000  # 2020-01-01
            prev = g.generate_or_abort_core(ts, ALLOWANCE)
            assert prev is not None
            for _ in range(N_LOOPS):
                ts += 16
                curr = g.generate_or_abort_core(ts, ALLOWANCE)
                assert curr is not None
                self._test_consecutive_pair(prev, curr)
                self.assertLess(curr.timestamp - (ts >> 8), ALLOWANCE >> 8)
                self.assertEqual(curr.node_ctr >> counter_size, node_id)

                prev = curr

            # keep monotonic order under mildly decreasing timestamps
            ts += ALLOWANCE * 16
            prev = g.generate_or_abort_core(ts, ALLOWANCE)
            assert prev is not None
            for _ in range(N_LOOPS):
                ts -= 16
                curr = g.generate_or_abort_core(ts, ALLOWANCE)
                assert curr is not None
                self._test_consecutive_pair(prev, curr)
                self.assertLess(curr.timestamp - (ts >> 8), ALLOWANCE >> 8)
                self.assertEqual(curr.node_ctr >> counter_size, node_id)

                prev = curr

            # abort with significantly decreasing timestamps
            ts += ALLOWANCE * 16
            g.generate_or_abort_core(ts, ALLOWANCE)
            ts -= ALLOWANCE
            for _ in range(N_LOOPS):
                ts -= 16
                self.assertIsNone(g.generate_or_abort_core(ts, ALLOWANCE))


class TestGeneratorAsync(unittest.IsolatedAsyncioTestCase):
    def now(self) -> int:
        return int(datetime.datetime.now().timestamp() * 1_000) >> 8

    async def test_clock_integration(self) -> None:
        """Embeds up-to-date timestamp."""
        for _, _, node_spec in NODE_SPECS:
            g = Scru64Generator.parse(node_spec)
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
