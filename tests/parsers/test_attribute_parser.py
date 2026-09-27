import unittest

from tibiawikisql.parsers.base import AttributeParser


class TestAttributeParserVersion(unittest.TestCase):
    def test_version_lowercases_implemented(self):
        self.assertEqual("pre-6.0", AttributeParser.version()({"implemented": "Pre-6.0"}))

    def test_version_none_without_implemented(self):
        self.assertIsNone(AttributeParser.version()({}))

    def test_version_ignores_implementation(self):
        self.assertIsNone(AttributeParser.version()({"implementation": "15.32"}))
