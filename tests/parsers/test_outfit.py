import datetime
import unittest

from tests import load_resource
from tibiawikisql.api import Article
from tibiawikisql.models import Outfit
from tibiawikisql.parsers import OutfitParser


class TestOutfitParserClientIds(unittest.TestCase):
    def _parse(self, content: str) -> Outfit:
        article = Article(
            article_id=1,
            title="Barbarian Outfits",
            timestamp=datetime.datetime.fromisoformat("2018-08-20T04:33:15+00:00"),
            content=content,
        )

        return OutfitParser.from_article(article)

    def _edited(self, old: str, new: str) -> str:
        content = load_resource("content_outfit.txt")
        self.assertIn(old, content)
        return content.replace(old, new)

    def test_outfit_client_ids(self):
        outfit = self._parse(load_resource("content_outfit.txt"))

        self.assertEqual((143, 147), (outfit.male_client_id, outfit.female_client_id))

    def test_outfit_client_ids_none_without_lines(self):
        content = self._edited("| male_id\t= 143\n| female_id\t= 147\n", "")

        outfit = self._parse(content)

        self.assertEqual((None, None), (outfit.male_client_id, outfit.female_client_id))

    def test_outfit_client_id_none_when_empty(self):
        outfit = self._parse(self._edited("| male_id\t= 143", "| male_id\t="))

        self.assertIsNone(outfit.male_client_id)
        self.assertEqual(147, outfit.female_client_id)

    def test_outfit_client_id_none_when_not_numeric(self):
        outfit = self._parse(self._edited("| male_id\t= 143", "| male_id\t= abc"))

        self.assertIsNone(outfit.male_client_id)
        self.assertEqual(147, outfit.female_client_id)
