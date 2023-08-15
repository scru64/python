from __future__ import annotations

import unittest

from scru64 import NodeSpec, Scru64Id

from . import EXAMPLE_NODE_SPECS


class TestNodeSpec(unittest.TestCase):
    def test_constructor(self) -> None:
        """Initializes with node ID and size pair and node spec string."""
        for e in EXAMPLE_NODE_SPECS:
            node_prev = Scru64Id(e.node_prev)

            with_node_prev = NodeSpec(node_prev, e.node_id_size)
            self.assertEqual(with_node_prev.node_id(), e.node_id)
            self.assertEqual(with_node_prev.node_id_size(), e.node_id_size)
            if with_node_prev.node_prev() is not None:
                self.assertEqual(with_node_prev.node_prev(), node_prev)
            self.assertEqual(with_node_prev._node_prev, node_prev)
            self.assertEqual(str(with_node_prev), e.canonical)

            with_node_id = NodeSpec(e.node_id, e.node_id_size)
            self.assertEqual(with_node_id.node_id(), e.node_id)
            self.assertEqual(with_node_id.node_id_size(), e.node_id_size)
            self.assertIsNone(with_node_id.node_prev())
            if e.spec_type.endswith("_node_id"):
                self.assertEqual(with_node_id._node_prev, node_prev)
                self.assertEqual(str(with_node_prev), e.canonical)

            parsed = NodeSpec.parse(e.node_spec)
            self.assertEqual(parsed.node_id(), e.node_id)
            self.assertEqual(parsed.node_id_size(), e.node_id_size)
            if parsed.node_prev() is not None:
                self.assertEqual(parsed.node_prev(), node_prev)
            self.assertEqual(parsed._node_prev, node_prev)
            self.assertEqual(str(parsed), e.canonical)

    def test_constructor_error(self) -> None:
        """Fails to initialize with invalid node spec string."""
        cases = [
            "",
            "42",
            "/8",
            "42/",
            " 42/8",
            "42/8 ",
            " 42/8 ",
            "42 / 8",
            "+42/8",
            "42/+8",
            "-42/8",
            "42/-8",
            "ab/8",
            "1/2/3",
            "0/0",
            "0/24",
            "8/1",
            "1024/8",
            "0000000000001/8",
            "1/0016",
        ]

        for e in cases:
            with self.assertRaises(Exception):
                NodeSpec.parse(e)
