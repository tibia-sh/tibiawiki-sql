import datetime
import unittest

from tests import load_resource
from tibiawikisql.api import Article
from tibiawikisql.models import Mount
from tibiawikisql.parsers import MountParser


class TestMountParserClientId(unittest.TestCase):
    def _parse(self, content: str) -> Mount:
        article = Article(
            article_id=1,
            title="Doombringer",
            timestamp=datetime.datetime.fromisoformat("2018-08-20T04:33:15+00:00"),
            content=content,
        )

        return MountParser.from_article(article)

    def _edited(self, old: str, new: str) -> str:
        content = load_resource("content_mount.txt")
        self.assertIn(old, content)
        return content.replace(old, new)

    def test_mount_client_id(self):
        mount = self._parse(load_resource("content_mount.txt"))

        self.assertEqual(644, mount.client_id)

    def test_mount_client_id_none_without_line(self):
        mount = self._parse(self._edited("| mount_id\t= 644\n", ""))

        self.assertIsNone(mount.client_id)

    def test_mount_client_id_none_when_empty(self):
        mount = self._parse(self._edited("| mount_id\t= 644", "| mount_id\t="))

        self.assertIsNone(mount.client_id)
        self.assertEqual(10, mount.speed)

    def test_mount_client_id_none_when_not_numeric(self):
        mount = self._parse(self._edited("| mount_id\t= 644", "| mount_id\t= abc"))

        self.assertIsNone(mount.client_id)

    def test_mount_client_id_none_when_only_a_comment(self):
        mount = self._parse(self._edited("| mount_id\t= 644", "| mount_id\t= <!-- objectID: 51952-->"))

        self.assertIsNone(mount.client_id)


class TestMountParserMissingFields(unittest.TestCase):
    def _parse(self, title: str, resource: str) -> Mount:
        article = Article(
            article_id=1,
            title=title,
            timestamp=datetime.datetime.fromisoformat("2026-08-06T21:35:46+00:00"),
            content=load_resource(resource),
        )

        return MountParser.from_article(article)

    def test_mount_without_taming_method_or_version(self):
        mount = self._parse("Landsailer", "content_mount_landsailer.txt")

        self.assertIsNone(mount.taming_method)
        self.assertIsNone(mount.version)
        self.assertEqual(10, mount.speed)
        self.assertEqual(140, mount.price)
        self.assertIsNone(mount.client_id)

    def test_mount_with_taming_method_and_version(self):
        mount = self._parse("Doombringer", "content_mount.txt")

        self.assertEqual("Buying it on Tibia.com or via the Store.", mount.taming_method)
        self.assertEqual("10.56", mount.version)
