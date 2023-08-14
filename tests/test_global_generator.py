from __future__ import annotations

import os
import unittest

from scru64 import GlobalGenerator, new_string_sync, new_string

os.environ["SCRU64_NODE_SPEC"] = "42/8"


class TestGlobalGenerator(unittest.TestCase):
    def test_default_initializer(self) -> None:
        """Reads configuration from environment var."""
        self.assertEqual(GlobalGenerator.node_id(), 42)
        self.assertEqual(GlobalGenerator.node_id_size(), 8)
        self.assertEqual(str(GlobalGenerator.node_spec()), "42/8")

    def test_new_string_sync(self) -> None:
        """Generates 10k monotonically increasing IDs"""
        prev = new_string_sync()
        for i in range(10_000):
            curr = new_string_sync()
            self.assertLess(prev, curr)
            prev = curr


class TestGlobalGeneratorAsync(unittest.IsolatedAsyncioTestCase):
    async def test_new_string(self) -> None:
        """Generates 10k monotonically increasing IDs"""
        prev = await new_string()
        for i in range(10_000):
            curr = await new_string()
            self.assertLess(prev, curr)
            prev = curr
