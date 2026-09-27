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


class TestMountPriceCurrency(unittest.TestCase):
    def _parse(self, title: str, content: str) -> Mount:
        article = Article(
            article_id=1,
            title=title,
            timestamp=datetime.datetime.fromisoformat("2026-08-06T21:35:46+00:00"),
            content=content,
        )

        return MountParser.from_article(article)

    def _edited(self, old: str, new: str) -> str:
        content = load_resource("content_mount.txt")
        self.assertIn(old, content)
        return content.replace(old, new)

    def test_price_currency_from_pricecurrency(self):
        mount = self._parse("Landsailer", load_resource("content_mount_landsailer.txt"))

        self.assertEqual(140, mount.price)
        self.assertEqual("Event Points", mount.price_currency)

    def test_price_currency_defaults_to_tibia_coins(self):
        mount = self._parse("Doombringer", load_resource("content_mount.txt"))

        self.assertEqual(780, mount.price)
        self.assertEqual("Tibia Coins", mount.price_currency)

    def test_price_currency_tournament_coins(self):
        mount = self._parse("Doombringer", self._edited("| price         = 780\n",
                                                        "| price         = 780\n| tournament    = yes\n"))

        self.assertEqual(780, mount.price)
        self.assertEqual("Tournament Coins", mount.price_currency)

    def test_price_currency_none_without_price(self):
        mount = self._parse("Doombringer", self._edited("| price         = 780\n",
                                                        "| pricecurrency = Event Points\n"))

        self.assertIsNone(mount.price)
        self.assertIsNone(mount.price_currency)

    def test_pricecurrency_wins_over_tournament(self):
        mount = self._parse("Doombringer", self._edited(
            "| price         = 780\n",
            "| price         = 780\n| pricecurrency = Event Points\n| tournament    = yes\n",
        ))

        self.assertEqual("Event Points", mount.price_currency)

    def _priced_in(self, currency: str) -> Mount:
        return self._parse("Doombringer", self._edited("| price         = 780\n",
                                                       f"| price         = 780\n| pricecurrency = {currency}\n"))

    def test_price_currency_link_target(self):
        mount = self._priced_in("[[Silver Token]]s")

        self.assertEqual("Silver Token", mount.price_currency)

    def test_price_currency_template_without_parameters(self):
        mount = self._priced_in("{{Foo}}")

        self.assertEqual("Foo", mount.price_currency)

    def test_price_currency_tibia_coins_template(self):
        mount = self._priced_in("{{TC}}")

        self.assertEqual("Tibia Coins", mount.price_currency)

    def test_price_currency_tournament_coins_template(self):
        mount = self._priced_in("{{TC3}}")

        self.assertEqual("Tournament Coins", mount.price_currency)

    def test_price_currency_template_first_letter_any_case(self):
        mount = self._priced_in("{{tC}}")

        self.assertEqual("Tibia Coins", mount.price_currency)

    def test_price_currency_kept_for_zero_price(self):
        mount = self._parse("Doombringer", self._edited("| price         = 780\n", "| price         = 0\n"))

        self.assertEqual(0, mount.price)
        self.assertEqual("Tibia Coins", mount.price_currency)
