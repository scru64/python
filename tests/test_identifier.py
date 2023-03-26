from __future__ import annotations

import typing
import unittest

from scru64 import Scru64Id


class TestIdentifier(unittest.TestCase):
    def test_eq(self) -> None:
        """Supports equality comparison."""
        prev = Scru64Id(TEST_CASES[-1].num)
        for e in TEST_CASES:
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
        cases = sorted(TEST_CASES, key=lambda e: e.num)

        prev = Scru64Id(cases.pop(0).num)
        for e in cases:
            curr = Scru64Id(e.num)

            self.assertLess(prev, curr)
            self.assertLessEqual(prev, curr)

            self.assertGreater(curr, prev)
            self.assertGreaterEqual(curr, prev)

            prev = curr

    def test_convert_to(self) -> None:
        """Converts to various types."""
        for e in TEST_CASES:
            x = Scru64Id(e.num)

            self.assertEqual(int(x), e.num)
            self.assertEqual(str(x), e.text)
            self.assertEqual(x.timestamp, e.timestamp)
            self.assertEqual(x.node_ctr, e.node_ctr)

    def test_convert_from(self) -> None:
        """Converts from various types."""
        for e in TEST_CASES:
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


class PreparedCase(typing.NamedTuple):
    text: str
    num: int
    timestamp: int
    node_ctr: int


TEST_CASES: list[PreparedCase] = [
    PreparedCase(text="000000000000", num=0x0000000000000000, timestamp=0, node_ctr=0),
    PreparedCase(
        text="00000009zldr", num=0x0000000000FFFFFF, timestamp=0, node_ctr=16777215
    ),
    PreparedCase(
        text="zzzzzzzq0em8", num=0x41C21CB8E0000000, timestamp=282429536480, node_ctr=0
    ),
    PreparedCase(
        text="zzzzzzzzzzzz",
        num=0x41C21CB8E0FFFFFF,
        timestamp=282429536480,
        node_ctr=16777215,
    ),
    PreparedCase(
        text="0u375nxqh5cq",
        num=0x0186D52BBE2A635A,
        timestamp=6557084606,
        node_ctr=2777946,
    ),
    PreparedCase(
        text="0u375nxqh5cr",
        num=0x0186D52BBE2A635B,
        timestamp=6557084606,
        node_ctr=2777947,
    ),
    PreparedCase(
        text="0u375nxqh5cs",
        num=0x0186D52BBE2A635C,
        timestamp=6557084606,
        node_ctr=2777948,
    ),
    PreparedCase(
        text="0u375nxqh5ct",
        num=0x0186D52BBE2A635D,
        timestamp=6557084606,
        node_ctr=2777949,
    ),
    PreparedCase(
        text="0u375ny0glr0",
        num=0x0186D52BBF2A4A1C,
        timestamp=6557084607,
        node_ctr=2771484,
    ),
    PreparedCase(
        text="0u375ny0glr1",
        num=0x0186D52BBF2A4A1D,
        timestamp=6557084607,
        node_ctr=2771485,
    ),
    PreparedCase(
        text="0u375ny0glr2",
        num=0x0186D52BBF2A4A1E,
        timestamp=6557084607,
        node_ctr=2771486,
    ),
    PreparedCase(
        text="0u375ny0glr3",
        num=0x0186D52BBF2A4A1F,
        timestamp=6557084607,
        node_ctr=2771487,
    ),
    PreparedCase(
        text="jdsf1we3ui4f",
        num=0x2367C8DFB2E6D23F,
        timestamp=152065073074,
        node_ctr=15127103,
    ),
    PreparedCase(
        text="j0afcjyfyi98",
        num=0x22B86EAAD6B2F7EC,
        timestamp=149123148502,
        node_ctr=11728876,
    ),
    PreparedCase(
        text="ckzyfc271xsn",
        num=0x16FC214296B29057,
        timestamp=98719318678,
        node_ctr=11702359,
    ),
    PreparedCase(
        text="t0vgc4c4b18n",
        num=0x3504295BADC14F07,
        timestamp=227703085997,
        node_ctr=12668679,
    ),
    PreparedCase(
        text="mwcrtcubk7bp",
        num=0x29D3C7553E748515,
        timestamp=179646715198,
        node_ctr=7636245,
    ),
    PreparedCase(
        text="g9ye86pgplu7",
        num=0x1DBB24363718AECF,
        timestamp=127693764151,
        node_ctr=1617615,
    ),
    PreparedCase(
        text="qmez19t9oeir",
        num=0x30A122FEF7CD6C83,
        timestamp=208861855479,
        node_ctr=13462659,
    ),
    PreparedCase(
        text="d81r595fq52m",
        num=0x18278838F0660F2E,
        timestamp=103742454000,
        node_ctr=6688558,
    ),
    PreparedCase(
        text="v0rbps7ay8ks",
        num=0x38A9E683BB4425EC,
        timestamp=243368625083,
        node_ctr=4466156,
    ),
    PreparedCase(
        text="z0jndjt42op2",
        num=0x3FF596748EA77186,
        timestamp=274703217806,
        node_ctr=10973574,
    ),
    PreparedCase(
        text="f2bembkd4zrb",
        num=0x1B844EB5D1AEBB07,
        timestamp=118183867857,
        node_ctr=11451143,
    ),
    PreparedCase(
        text="mkg0fd5p76pp",
        num=0x29391373AB449ABD,
        timestamp=177051235243,
        node_ctr=4496061,
    ),
]
