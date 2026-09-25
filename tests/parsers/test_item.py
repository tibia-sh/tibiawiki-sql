import datetime
import unittest

from tests import load_resource
from tibiawikisql.api import Article
from tibiawikisql.parsers import ItemParser


class TestItemParserRestores(unittest.TestCase):
    def _restores(self, title: str, content: str) -> dict[str, str]:
        article = Article(
            article_id=1,
            title=title,
            timestamp=datetime.datetime.fromisoformat("2018-08-20T04:33:15+00:00"),
            content=content,
        )

        item = ItemParser.from_article(article)

        return {a.name: a.value for a in item.attributes if a.name.startswith("restores_")}

    def _edited(self, resource: str, old: str, new: str) -> str:
        content = load_resource(resource)
        self.assertIn(old, content)
        return content.replace(old, new)

    def test_item_restores_health_potion(self):
        restores = self._restores("Health Potion", load_resource("content_item_potion_health_potion.txt"))

        self.assertEqual({"restores_hp_min": "125", "restores_hp_max": "175"}, restores)

    def test_item_restores_great_spirit_potion(self):
        restores = self._restores("Great Spirit Potion", load_resource("content_item_potion_great_spirit_potion.txt"))

        self.assertEqual(
            {
                "restores_hp_min": "250",
                "restores_hp_max": "350",
                "restores_mana_min": "125",
                "restores_mana_max": "185",
            },
            restores,
        )

    def test_item_restores_thousands_separator(self):
        restores = self._restores(
            "Supreme Health Potion",
            load_resource("content_item_potion_supreme_health_potion.txt"),
        )

        self.assertEqual({"restores_hp_min": "875", "restores_hp_max": "1175"}, restores)

    def test_item_restores_without_bold(self):
        restores = self._restores("Great Mana Potion", load_resource("content_item_potion_great_mana_potion.txt"))

        self.assertEqual({"restores_mana_min": "150", "restores_mana_max": "250"}, restores)

    def test_item_restores_capitalized(self):
        restores = self._restores(
            "Superior Mana Potion",
            load_resource("content_item_potion_superior_mana_potion.txt"),
        )

        self.assertEqual({"restores_mana_min": "240", "restores_mana_max": "360"}, restores)

    def test_item_restores_none_without_range(self):
        antidote = self._restores("Antidote Potion", load_resource("content_item_potion_antidote_potion.txt"))
        store = self._restores("Health Potion", load_resource("content_item_store.txt"))

        self.assertEqual({}, antidote)
        self.assertEqual({}, store)

    def test_item_restores_none_when_min_exceeds_max(self):
        content = self._edited(
            "content_item_potion_health_potion.txt",
            "restores between '''125''' and '''175 [[Hit Point]]s'''",
            "restores between 175 and 125 [[Hit Point]]s",
        )

        self.assertEqual({}, self._restores("Health Potion", content))

    def test_item_restores_none_when_unit_repeats(self):
        content = self._edited(
            "content_item_potion_great_spirit_potion.txt",
            "'''185 [[Mana Points]]'''",
            "'''185 [[Hit Points]]'''",
        )

        self.assertEqual({}, self._restores("Great Spirit Potion", content))

    def test_item_restores_none_when_second_min_exceeds_max(self):
        content = self._edited(
            "content_item_potion_great_spirit_potion.txt",
            "between '''125''' and '''185 [[Mana Points]]'''",
            "between '''185''' and '''125 [[Mana Points]]'''",
        )

        self.assertEqual({}, self._restores("Great Spirit Potion", content))

    def test_item_restores_none_when_amount_malformed(self):
        content = self._edited(
            "content_item_potion_great_spirit_potion.txt",
            "between '''125''' and '''185 [[Mana Points]]'''",
            "between '''12,5''' and '''185 [[Mana Points]]'''",
        )

        self.assertEqual({}, self._restores("Great Spirit Potion", content))
