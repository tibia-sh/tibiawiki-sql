import datetime
import unittest

from tests import load_resource
from tibiawikisql.api import Article
from tibiawikisql.errors import ArticleParsingError
from tibiawikisql.models import Charm
from tibiawikisql.parsers import CharmParser


class TestCharmParserCosts(unittest.TestCase):
    def _parse(self, title: str, content: str) -> Charm:
        article = Article(
            article_id=1,
            title=title,
            timestamp=datetime.datetime.fromisoformat("2026-08-06T21:35:46+00:00"),
            content=content,
        )

        return CharmParser.from_article(article)

    def _costs(self, charm: Charm) -> tuple[int, int, int]:
        return charm.cost_level_1, charm.cost_level_2, charm.cost_level_3

    def test_low_blow_costs_split_by_commas(self):
        charm = self._parse("Low Blow", load_resource("content_charm_low_blow.txt"))

        self.assertEqual((800, 1200, 4000), self._costs(charm))

    def test_costs_with_thousands_separator(self):
        content = load_resource("content_charm.txt")
        self.assertIn("| cost          = 360 / 540 / 1,800\n", content)

        charm = self._parse("Curse (Charm)", content)

        self.assertEqual((360, 540, 1800), self._costs(charm))

    def test_costs_not_three(self):
        content = load_resource("content_charm.txt").replace("360 / 540 / 1,800", "100 / 150")

        with self.assertRaisesRegex(ArticleParsingError, "Expected three charm costs"):
            self._parse("Curse (Charm)", content)
