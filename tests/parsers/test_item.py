import datetime
import os
import unittest

from tests import RESOURCES_PATH, load_resource
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

    def _inline(self, notes: str) -> str:
        return (
            "{{Infobox Object|List={{{1|}}}|GetValue={{{GetValue|}}}\n"
            "| name          = Test Item\n"
            f"| notes         = {notes}\n"
            "}}\n"
        )

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

    def test_item_restores_none_when_amount_too_long(self):
        content = self._edited(
            "content_item_potion_health_potion.txt",
            "'''175 [[Hit Point]]s'''",
            f"'''{'9' * 4400} [[Hit Point]]s'''",
        )

        self.assertEqual({}, self._restores("Health Potion", content))

    def test_item_restores_none_when_unit_runs_into_word(self):
        restores = self._restores("Test Item", self._inline("It restores between 1 and 3 manatees."))

        self.assertEqual({}, restores)

    def test_item_restores_unit_before_punctuation(self):
        restores = self._restores("Test Item", self._inline("It restores between 1 and 3 Hit Points."))

        self.assertEqual({"restores_hp_min": "1", "restores_hp_max": "3"}, restores)


class TestItemParserNumbers(unittest.TestCase):
    def _parse(self, title: str, resource: str):
        article = Article(
            article_id=1,
            title=title,
            timestamp=datetime.datetime.fromisoformat("2018-08-20T04:33:15+00:00"),
            content=load_resource(resource),
        )

        return ItemParser.from_article(article)

    def test_item_client_id_keeps_first_of_list(self):
        item = self._parse("Shallow Water", "content_item_shallow_water.txt")

        self.assertEqual(629, item.client_id)

    def test_item_value_buy_thousands_separator(self):
        item = self._parse("Amethyst Necklace", "content_item_amethyst_necklace.txt")

        self.assertEqual(4000, item.value_buy)


class TestItemParserBuyCurrency(unittest.TestCase):
    def _parse_content(self, title: str, content: str):
        article = Article(
            article_id=1,
            title=title,
            timestamp=datetime.datetime.fromisoformat("2018-08-20T04:33:15+00:00"),
            content=content,
        )

        return ItemParser.from_article(article)

    def _parse(self, title: str, resource: str):
        return self._parse_content(title, load_resource(resource))

    def test_item_value_buy_currency_from_pricecurrency(self):
        item = self._parse("25 Years Backpack", "content_item_25_years_backpack.txt")

        self.assertEqual(7197, item.value_buy)
        self.assertEqual("Theons", item.value_buy_currency)

    def test_item_value_buy_currency_template_without_parameters(self):
        content = load_resource("content_item_25_years_backpack.txt")
        self.assertIn("| pricecurrency = [[Theons]]\n", content)
        item = self._parse_content("25 Years Backpack",
                                   content.replace("| pricecurrency = [[Theons]]\n", "| pricecurrency = {{Foo}}\n"))

        self.assertEqual(7197, item.value_buy)
        self.assertEqual("Foo", item.value_buy_currency)

    def test_item_value_buy_currency_template_in_npcprice(self):
        content = load_resource("content_item_blade_of_mayhem.txt")
        self.assertIn("| npcprice      = 50 [[Gold Token]]s\n", content)
        item = self._parse_content("Blade of Mayhem",
                                   content.replace("| npcprice      = 50 [[Gold Token]]s\n", "| npcprice      = 50 {{Foo}}\n"))

        self.assertEqual(50, item.value_buy)
        self.assertEqual("Foo", item.value_buy_currency)

    def test_item_value_buy_currency_link_target(self):
        item = self._parse("Amethyst Necklace", "content_item_amethyst_necklace.txt")

        self.assertEqual(4000, item.value_buy)
        self.assertEqual("Trust Point", item.value_buy_currency)

    def test_item_value_buy_currency_defaults_to_gold(self):
        item = self._parse("Health Potion", "content_item_potion_health_potion.txt")

        self.assertEqual(50, item.value_buy)
        self.assertEqual("Gold Coin", item.value_buy_currency)

    def test_item_value_buy_currency_link_in_npcprice(self):
        item = self._parse("Blade of Mayhem", "content_item_blade_of_mayhem.txt")

        self.assertEqual(50, item.value_buy)
        self.assertEqual("Gold Token", item.value_buy_currency)

    def test_item_value_buy_currency_text_in_npcprice(self):
        item = self._parse("Frozen Crapace", "content_item_frozen_crapace.txt")

        self.assertEqual(250, item.value_buy)
        self.assertEqual("Christmas Token", item.value_buy_currency)

    def test_item_value_buy_currency_npcprice_suffix(self):
        content = load_resource("content_item_potion_health_potion.txt")
        self.assertIn("| npcprice      = 50\n", content)
        cases = [
            ("<span>50</span>", 50, "Gold Coin"),
            ("50<br>60", 50, "Gold Coin"),
            ("50 - 60", 50, "Gold Coin"),
            ("50 - 60 gp", 50, "Gold Coin"),
            ("50 gp (from [[Sam]])", 50, "Gold Coin"),
            ("50 (from [[Sam]]) [[Gold Token]]s", 50, "Gold Token"),
            ("50 <!-- note --> [[Gold Token]]s", 50, "Gold Token"),
            ("50 <small>[[Gold Token]]s</small>", 50, "Gold Token"),
            ("50 [[Gold Token]]s", 50, "Gold Token"),
            ("250 Christmas Token", 250, "Christmas Token"),
            ("0 - 30", 0, None),
        ]
        for npcprice, value_buy, currency in cases:
            with self.subTest(npcprice=npcprice):
                item = self._parse_content(
                    "Health Potion", content.replace("| npcprice      = 50\n", f"| npcprice      = {npcprice}\n"),
                )

                self.assertEqual(value_buy, item.value_buy)
                self.assertEqual(currency, item.value_buy_currency)

    def test_item_value_buy_currency_none_for_zero_range(self):
        item = self._parse("Adventurer's Stone", "content_item_adventurers_stone.txt")

        self.assertEqual(0, item.value_buy)
        self.assertIsNone(item.value_buy_currency)

    def test_item_value_buy_currency_none_when_not_sold(self):
        item = self._parse("Fire Sword", "content_item.txt")

        self.assertEqual(0, item.value_buy)
        self.assertIsNone(item.value_buy_currency)

    def test_item_value_buy_currency_none_without_npcprice(self):
        item = self._parse("Shallow Water", "content_item_shallow_water.txt")

        self.assertIsNone(item.value_buy)
        self.assertIsNone(item.value_buy_currency)


class TestItemParserSlotAndUsable(unittest.TestCase):
    def _parse_content(self, title: str, content: str):
        article = Article(
            article_id=1,
            title=title,
            timestamp=datetime.datetime.fromisoformat("2018-08-20T04:33:15+00:00"),
            content=content,
        )

        return ItemParser.from_article(article)

    def _edited(self, old: str, new: str):
        content = load_resource("content_item_amethyst_necklace.txt")
        self.assertIn(old, content)
        return self._parse_content("Amethyst Necklace", content.replace(old, new))

    def test_amethyst_necklace(self):
        item = self._parse_content("Amethyst Necklace", load_resource("content_item_amethyst_necklace.txt"))

        self.assertEqual("neck", item.slot)
        self.assertIs(False, item.is_usable)

    def test_blade_of_mayhem(self):
        item = self._parse_content("Blade of Mayhem", load_resource("content_item_blade_of_mayhem.txt"))

        self.assertEqual("weapon hand", item.slot)
        self.assertIs(True, item.is_usable)

    def test_slot_unknown(self):
        item = self._edited("| slot          = Neck", "| slot          = ?")

        self.assertIsNone(item.slot)

    def test_slot_uncertain(self):
        item = self._edited("| slot          = Neck", "| slot          = Neck?")

        self.assertIsNone(item.slot)

    def test_slot_empty(self):
        item = self._edited("| slot          = Neck", "| slot          =")

        self.assertIsNone(item.slot)

    def test_slot_absent(self):
        item = self._edited("| slot          = Neck\n", "")

        self.assertIsNone(item.slot)

    def test_slot_ignores_a_trailing_comment(self):
        item = self._edited("| slot          = Neck", "| slot          = Neck <!-- Ring? -->")

        self.assertEqual("neck", item.slot)

    def test_slot_only_in_a_comment(self):
        item = self._edited("| slot          = Neck", "| slot          = <!-- Neck -->")

        self.assertIsNone(item.slot)

    def test_usable_unknown(self):
        item = self._edited("| usable        = no", "| usable        = ?")

        self.assertIsNone(item.is_usable)

    def test_usable_absent(self):
        item = self._edited("| usable        = no\n", "")

        self.assertIsNone(item.is_usable)

    def test_usable_typo(self):
        item = self._edited("| usable        = no", "| usable        = noo")

        self.assertIsNone(item.is_usable)

    def test_usable_ignores_a_trailing_comment(self):
        item = self._edited("| usable        = no", "| usable        = yes <!-- x -->")

        self.assertIs(True, item.is_usable)


class TestItemParserClientIds(unittest.TestCase):
    def _parse_content(self, title: str, content: str):
        article = Article(
            article_id=1,
            title=title,
            timestamp=datetime.datetime.fromisoformat("2018-08-20T04:33:15+00:00"),
            content=content,
        )

        return ItemParser.from_article(article)

    def _edited(self, old: str, new: str):
        content = load_resource("content_item_amethyst_necklace.txt")
        self.assertIn(old, content)
        return self._parse_content("Amethyst Necklace", content.replace(old, new))

    def test_shallow_water_keeps_every_id(self):
        item = self._parse_content("Shallow Water", load_resource("content_item_shallow_water.txt"))

        self.assertEqual([629, 630, 631, 632, 633, 634], item.client_ids)
        self.assertEqual(item.client_id, item.client_ids[0])

    def test_single_id(self):
        item = self._parse_content("Amethyst Necklace", load_resource("content_item_amethyst_necklace.txt"))

        self.assertEqual([35609], item.client_ids)
        self.assertEqual(35609, item.client_id)

    def test_ids_separated_by_comma_and_space(self):
        item = self._parse_content("Football", load_resource("content_item_no_attrib.txt"))

        self.assertEqual([2990, 9104], item.client_ids)

    def test_absent(self):
        item = self._edited("| itemid        = 35609\n", "")

        self.assertEqual([], item.client_ids)

    def test_unknown(self):
        item = self._edited("| itemid        = 35609", "| itemid        = ?")

        self.assertEqual([], item.client_ids)

    def test_only_in_a_comment(self):
        item = self._edited("| itemid        = 35609", "| itemid        = <!-- 35609 -->")

        self.assertEqual([], item.client_ids)

    def test_ignores_a_trailing_comment(self):
        item = self._edited("| itemid        = 35609", "| itemid        = 35609 <!-- 35610 -->")

        self.assertEqual([35609], item.client_ids)

    def test_client_id_reads_a_leading_comment_the_rows_ignore(self):
        item = self._edited("| itemid        = 35609", "| itemid        = <!-- 7 -->644,645")

        self.assertEqual(7, item.client_id)
        self.assertEqual([644, 645], item.client_ids)

    def test_client_id_reads_a_comment_only_value_with_no_rows(self):
        item = self._edited("| itemid        = 35609", "| itemid        = <!-- 7 -->")

        self.assertEqual(7, item.client_id)
        self.assertEqual([], item.client_ids)

    def _item_fixtures(self) -> list[str]:
        resources = sorted(
            name for name in os.listdir(RESOURCES_PATH)
            if name.startswith("content_item") and "{{Infobox Object" in load_resource(name)
        )
        self.assertGreaterEqual(len(resources), 19)
        return resources

    def test_every_item_fixture_has_a_client_id(self):
        for resource in self._item_fixtures():
            with self.subTest(resource=resource):
                item = self._parse_content(resource, load_resource(resource))

                self.assertTrue(item.client_ids)

    def test_first_id_matches_client_id_in_every_item_fixture(self):
        for resource in self._item_fixtures():
            with self.subTest(resource=resource):
                item = self._parse_content(resource, load_resource(resource))

                if item.client_ids:
                    self.assertEqual(item.client_id, item.client_ids[0])
