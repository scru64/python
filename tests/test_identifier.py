from __future__ import annotations

import unittest

from scru64 import Scru64Id

from . import EXAMPLE_IDS


class TestIdentifier(unittest.TestCase):
    def test_eq(self) -> None:
        """Supports equality comparison."""
        prev = Scru64Id(EXAMPLE_IDS[-1].num)
        for e in EXAMPLE_IDS:
            curr = Scru64Id(e.num)
            twin = Scru64Id(e.num)

            self.assertIsNot(curr, twin)
            self.assertEqual(curr, twin)
            self.assertEqual(twin, curr)
            self.assertEqual(int(curr), int(twin))
            self.assertEqual(str(curr), str(twin))
            self.assertEqual(curr.timestamp, twin.timestamp)
            self.assertEqual(curr.node_ctr, twin.node_ctr)
            self.assertEqual(hash(curr), hash(twin))

            self.assertIsNot(curr, prev)
            self.assertNotEqual(prev, curr)
            self.assertNotEqual(curr, prev)
            self.assertNotEqual(int(curr), int(prev))
            self.assertNotEqual(str(curr), str(prev))
            self.assertTrue(
                (curr.timestamp != prev.timestamp) or (curr.node_ctr != prev.node_ctr)
            )
            self.assertNotEqual(hash(curr), hash(prev))

            prev = curr

    def test_ord(self) -> None:
        """Supports ordering comparison."""
        cases = sorted(EXAMPLE_IDS, key=lambda e: e.num)

        prev = Scru64Id(cases.pop(0).num)
        for e in cases:
            curr = Scru64Id(e.num)

            self.assertLess(prev, curr)
            self.assertLessEqual(prev, curr)

            self.assertGreater(curr, prev)
            self.assertGreaterEqual(curr, prev)

            self.assertLess(int(prev), int(curr))
            self.assertLess(str(prev), str(curr))

            prev = curr

    def test_convert_to(self) -> None:
        """Converts to various types."""
        for e in EXAMPLE_IDS:
            x = Scru64Id(e.num)

            self.assertEqual(int(x), e.num)
            self.assertEqual(str(x), e.text)
            self.assertEqual(x.timestamp, e.timestamp)
            self.assertEqual(x.node_ctr, e.node_ctr)

    def test_convert_from(self) -> None:
        """Converts from various types."""
        for e in EXAMPLE_IDS:
            x = Scru64Id(e.num)

            self.assertEqual(x, Scru64Id.from_str(e.text))
            self.assertEqual(x, Scru64Id.from_str(e.text.upper()))
            self.assertEqual(x, Scru64Id.from_parts(e.timestamp, e.node_ctr))

    def test_from_int_error(self) -> None:
        """Rejects integer out of valid range."""
        with self.assertRaises(ValueError):
            Scru64Id(36**12)
        with self.assertRaises(ValueError):
            Scru64Id(2**64 - 1)

        with self.assertRaises(ValueError):
            Scru64Id(-1)
        with self.assertRaises(ValueError):
            Scru64Id(-(2**63))

    def test_parse_error(self) -> None:
        """Fails to parse invalid textual representations."""
        cases = [
            "",
            " 0u3wrp5g81jx",
            "0u3wrp5g81jy ",
            " 0u3wrp5g81jz ",
            "+0u3wrp5g81k0",
            "-0u3wrp5g81k1",
            "+u3wrp5q7ta5",
            "-u3wrp5q7ta6",
            "0u3w_p5q7ta7",
            "0u3wrp5-7ta8",
            "0u3wrp5q7t 9",
        ]

        for e in cases:
            with self.assertRaises(ValueError):
                Scru64Id.from_str(e)

    def test_from_parts_error(self) -> None:
        """Rejects `MAX + 1` even if passed as pair of fields."""
        max = 36**12 - 1
        with self.assertRaises(ValueError):
            Scru64Id.from_parts(max >> 24, (max & 0xFF_FFFF) + 1)
        with self.assertRaises(ValueError):
            Scru64Id.from_parts((max >> 24) + 1, 0)
