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
