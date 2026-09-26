# Changed by tibia.sh in 2026. See "About this copy" in README.md.
import datetime
import re
import unittest

from tests import load_resource
from tibiawikisql.api import Article
from tibiawikisql.models import Npc
from tibiawikisql.parsers import NpcParser


class TestNpcParser(unittest.TestCase):
    def test_npc_parser_from_article_success(self):
        article = Article(
            article_id=1,
            title="Yaman",
            timestamp=datetime.datetime.fromisoformat("2018-08-20T04:33:15+00:00"),
            content=load_resource("content_npc.txt"),
        )

        npc = NpcParser.from_article(article)

        self.assertIsInstance(npc, Npc)
        self.assertEqual("Yaman", npc.title)
        self.assertEqual("Djinn", npc.race)
        self.assertEqual(1, len(npc.races))

    def test_npc_parser_from_article_travel_destinations(self):
        article = Article(
            article_id=1,
            title="Captain Bluebear",
            timestamp=datetime.datetime.fromisoformat("2018-08-20T04:33:15+00:00"),
            content=load_resource("content_npc_travel.txt"),
        )

        npc = NpcParser.from_article(article)

        self.assertIsInstance(npc, Npc)
        self.assertEqual("Captain Bluebear", npc.title)
        self.assertEqual("Human", npc.race)
        self.assertEqual(10, len(npc.destinations))

    def test_npc_parser_locations_all_positions(self):
        article = Article(
            article_id=1,
            title="Buddel",
            timestamp=datetime.datetime.fromisoformat("2018-08-20T04:33:15+00:00"),
            content=load_resource("content_npc_locations.txt"),
        )

        npc = NpcParser.from_article(article)

        self.assertEqual(
            [
                (1, "Svargrond", None, 32254, 31195, 7),
                (2, "Svargrond", "Okolnir", 32225, 31381, 7),
                (3, "Svargrond", "Helheim", 32464, 31172, 7),
                (4, "Svargrond", "Tyrsung", 32332, 31229, 7),
                (5, "Svargrond", "Krimhorn", 32019, 31293, 7),
            ],
            [(p.position, p.city, p.subarea, p.x, p.y, p.z) for p in npc.locations],
        )

    def test_npc_parser_locations_single(self):
        article = Article(
            article_id=1,
            title="Captain Bluebear",
            timestamp=datetime.datetime.fromisoformat("2018-08-20T04:33:15+00:00"),
            content=load_resource("content_npc_travel.txt"),
        )

        npc = NpcParser.from_article(article)

        self.assertEqual(1, len(npc.locations))
        location = npc.locations[0]
        self.assertEqual(1, location.position)
        self.assertEqual(
            (npc.city, npc.x, npc.y, npc.z),
            (location.city, location.x, location.y, location.z),
        )

    def test_npc_parser_locations_position_7_and_geolabel(self):
        content = (
            "{{Infobox NPC|List={{{1|}}}|GetValue={{{GetValue|}}}\n"
            "| name         = Test NPC\n"
            "| city         = Thais\n"
            "| city7        = Carlin\n"
            "| geolabel7    = [[Carlin Harbour|Harbour]]\n"
            "| posx7        = 125.1.2\n"
            "| posy7        = 124.10\n"
            "}}\n"
        )
        article = Article(
            article_id=1,
            title="Test NPC",
            timestamp=datetime.datetime.fromisoformat("2018-08-20T04:33:15+00:00"),
            content=content,
        )

        npc = NpcParser.from_article(article)

        self.assertEqual([1, 7], [p.position for p in npc.locations])
        position_7 = npc.locations[1]
        self.assertEqual("Carlin", position_7.city)
        self.assertEqual("Harbour", position_7.geolabel)
        self.assertIsNone(position_7.x)
        self.assertEqual(31754, position_7.y)
        self.assertIsNone(position_7.z)

    def test_npc_parser_locations_malformed_and_gaps(self):
        content = load_resource("content_npc_locations.txt")
        content = re.sub(r"^\| posx2\s*=.*$", "| posx2        = 125", content, flags=re.MULTILINE)
        content = re.sub(r"^\| posy2\s*=.*$", "| posy2        = abc", content, flags=re.MULTILINE)
        content = re.sub(r"^\| posx4\s*=.*$", "| posx4        =", content, flags=re.MULTILINE)
        content = re.sub(r"^\| (city|subarea|posx|posy|posz)3\s*=.*\n", "", content, flags=re.MULTILINE)
        article = Article(
            article_id=1,
            title="Buddel",
            timestamp=datetime.datetime.fromisoformat("2018-08-20T04:33:15+00:00"),
            content=content,
        )

        npc = NpcParser.from_article(article)

        self.assertEqual([1, 2, 4, 5], [p.position for p in npc.locations])
        position_2 = npc.locations[1]
        self.assertEqual(32000, position_2.x)
        self.assertIsNone(position_2.y)
        self.assertEqual("Okolnir", position_2.subarea)
        position_4 = npc.locations[2]
        self.assertIsNone(position_4.x)
        self.assertEqual(31229, position_4.y)

    def test_npc_destinations_origin_from_note(self):
        article = Article(
            article_id=1,
            title="Sebastian",
            timestamp=datetime.datetime.fromisoformat("2018-08-20T04:33:15+00:00"),
            content=load_resource("content_npc_multi_origin.txt"),
        )

        npc = NpcParser.from_article(article)

        self.assertEqual(
            [
                ("Liberty Bay", 50, "Meriana"),
                ("Liberty Bay", 100, "Nargor"),
                ("Meriana", 50, "Liberty Bay"),
                ("Nargor", 50, "Liberty Bay"),
            ],
            [(d.name, d.price, d.origin) for d in npc.destinations],
        )
        self.assertEqual("From Meriana", npc.destinations[0].notes)

    def test_npc_destinations_origin_mid_sentence(self):
        article = Article(
            article_id=1,
            title="Maris",
            timestamp=datetime.datetime.fromisoformat("2018-08-20T04:33:15+00:00"),
            content=load_resource("content_npc_origin_note.txt"),
        )

        npc = NpcParser.from_article(article)

        self.assertEqual(
            [("Fenrock", 100, "Yalahar"), ("Mistrock", 100, "Yalahar"), ("Yalahar", 100, None)],
            [(d.name, d.price, d.origin) for d in npc.destinations],
        )

    def test_npc_destinations_origin_default(self):
        article = Article(
            article_id=1,
            title="Captain Bluebear",
            timestamp=datetime.datetime.fromisoformat("2018-08-20T04:33:15+00:00"),
            content=load_resource("content_npc_travel.txt"),
        )

        npc = NpcParser.from_article(article)

        self.assertTrue(npc.destinations)
        self.assertEqual(["Thais"] * len(npc.destinations), [d.origin for d in npc.destinations])

    def test_npc_destinations_origin_legacy_transport(self):
        content = (
            "{{Infobox NPC|List={{{1|}}}|GetValue={{{GetValue|}}}\n"
            "| name         = Test NPC\n"
            "| city         = Thais\n"
            "| notes        = {{Transport|Carlin, 110|Thais, 0}}\n"
            "}}\n"
        )
        article = Article(
            article_id=1,
            title="Test NPC",
            timestamp=datetime.datetime.fromisoformat("2018-08-20T04:33:15+00:00"),
            content=content,
        )

        npc = NpcParser.from_article(article)

        self.assertEqual(
            [("Carlin", 110, "Thais"), ("Thais", 0, None)],
            [(d.name, d.price, d.origin) for d in npc.destinations],
        )

    def test_npc_destinations_origin_named_note_parameter(self):
        content = (
            "{{Infobox NPC|List={{{1|}}}|GetValue={{{GetValue|}}}\n"
            "| name         = Test NPC\n"
            "| city         = Liberty Bay\n"
            "| notes        = {{TransportList|discount=no\n"
            " |{{TransportCell|Liberty Bay|50|3=From [[Meriana]]}}\n"
            "}}\n"
            "}}\n"
        )
        article = Article(
            article_id=1,
            title="Test NPC",
            timestamp=datetime.datetime.fromisoformat("2018-08-20T04:33:15+00:00"),
            content=content,
        )

        npc = NpcParser.from_article(article)

        self.assertEqual([("Liberty Bay", 50, "Meriana")], [(d.name, d.price, d.origin) for d in npc.destinations])

    def _parse_inline_npc(self, city: str, notes: str, positions: str = "") -> Npc:
        content = (
            "{{Infobox NPC|List={{{1|}}}|GetValue={{{GetValue|}}}\n"
            "| name         = Test NPC\n"
            f"| city         = {city}\n"
            f"{positions}"
            f"| notes        = {notes}\n"
            "}}\n"
        )
        article = Article(
            article_id=1,
            title="Test NPC",
            timestamp=datetime.datetime.fromisoformat("2018-08-20T04:33:15+00:00"),
            content=content,
        )
        return NpcParser.from_article(article)

    def test_npc_destinations_origin_plain_text_note(self):
        npc = self._parse_inline_npc(
            "Liberty Bay",
            "{{TransportList|discount=no\n |{{TransportCell|Meriana|50|From Meriana}}\n}}",
        )

        self.assertEqual([("Meriana", 50, "Liberty Bay")], [(d.name, d.price, d.origin) for d in npc.destinations])

    def test_npc_destinations_origin_piped_link_uses_target(self):
        npc = self._parse_inline_npc(
            "Liberty Bay",
            "{{TransportList|discount=no\n |{{TransportCell|Liberty Bay|50|From [[Meriana Docks|Meriana]]}}\n}}",
        )

        self.assertEqual(
            [("Liberty Bay", 50, "Meriana Docks")],
            [(d.name, d.price, d.origin) for d in npc.destinations],
        )

    def test_npc_destinations_origin_same_city_ignores_case(self):
        npc = self._parse_inline_npc(
            "Liberty Bay",
            "{{TransportList|discount=no\n |{{TransportCell|liberty bay|50}}\n}}",
        )

        self.assertEqual([("liberty bay", 50, None)], [(d.name, d.price, d.origin) for d in npc.destinations])

    def test_npc_destinations_origin_shuttle_by_city_and_subarea(self):
        article = Article(
            article_id=1,
            title="Harlow",
            timestamp=datetime.datetime.fromisoformat("2018-08-20T04:33:15+00:00"),
            content=load_resource("content_npc_origin_position.txt"),
        )

        npc = NpcParser.from_article(article)

        self.assertEqual(
            [("Vengoth", 100, "Yalahar"), ("Yalahar", 50, "Vengoth")],
            [(d.name, d.price, d.origin) for d in npc.destinations],
        )

    def test_npc_destinations_origin_shuttle_by_geolabel(self):
        article = Article(
            article_id=1,
            title="Tarak",
            timestamp=datetime.datetime.fromisoformat("2018-08-20T04:33:15+00:00"),
            content=load_resource("content_npc_shuttle.txt"),
        )

        npc = NpcParser.from_article(article)

        self.assertEqual(
            [("Monument Tower", 50, "Sunken Quarter"), ("Sunken Quarter", 0, "Monument Tower")],
            [(d.name, d.price, d.origin) for d in npc.destinations],
        )

    def test_npc_destinations_origin_not_shuttle_when_both_positions_match_one_destination(self):
        npc = self._parse_inline_npc(
            "Thais",
            "{{TransportList|discount=no\n"
            " |{{TransportCell|Carlin|110}}\n"
            " |{{TransportCell|thais|110}}\n"
            "}}",
            "| city2        = Thais\n",
        )

        self.assertEqual(
            [("Carlin", 110, "Thais"), ("thais", 110, None)],
            [(d.name, d.price, d.origin) for d in npc.destinations],
        )

    def test_npc_destinations_origin_not_shuttle_when_a_position_matches_both_destinations(self):
        npc = self._parse_inline_npc(
            "Yalahar",
            "{{TransportList|discount=no\n"
            " |{{TransportCell|Vengoth|100}}\n"
            " |{{TransportCell|Yalahar|50}}\n"
            "}}",
            "| subarea      = Vengoth\n"
            "| city2        = Yalahar\n",
        )

        self.assertEqual(
            [("Vengoth", 100, "Yalahar"), ("Yalahar", 50, None)],
            [(d.name, d.price, d.origin) for d in npc.destinations],
        )

    def test_npc_destinations_origin_shuttle_note_wins(self):
        npc = self._parse_inline_npc(
            "Farmine",
            "{{TransportList|discount=no\n"
            " |{{TransportCell|Vengoth|100|From [[Trade Quarter]]}}\n"
            " |{{TransportCell|Yalahar|50}}\n"
            "}}",
            "| subarea      = Vengoth\n"
            "| city2        = Yalahar\n",
        )

        self.assertEqual(
            [("Vengoth", 100, "Trade Quarter"), ("Yalahar", 50, "Vengoth")],
            [(d.name, d.price, d.origin) for d in npc.destinations],
        )

    def test_npc_destinations_origin_city_when_another_city_position_differs(self):
        npc = self._parse_inline_npc(
            "Thais",
            "{{TransportList|discount=no\n"
            " |{{TransportCell|Kazordoon|100}}\n"
            " |{{TransportCell|Robson's Isle|100}}\n"
            " |{{TransportCell|Thais|100}}\n"
            "}}",
            "| subarea      = Underground Isle\n"
            "| geolabel     = Robson's Isle\n"
            "| city2        = Thais\n"
            "| city3        = Kazordoon\n",
        )

        self.assertEqual(
            [("Kazordoon", 100, "Thais"), ("Robson's Isle", 100, "Thais"), ("Thais", 100, None)],
            [(d.name, d.price, d.origin) for d in npc.destinations],
        )

    def test_npc_destinations_origin_null_when_subarea_matches_ignoring_case(self):
        npc = self._parse_inline_npc(
            "Farmine",
            "{{TransportList|discount=no\n |{{TransportCell|vengoth|100}}\n}}",
            "| subarea      = Vengoth\n",
        )

        self.assertEqual([("vengoth", 100, None)], [(d.name, d.price, d.origin) for d in npc.destinations])

    def test_npc_destinations_origin_null_when_geolabel_matches(self):
        npc = self._parse_inline_npc(
            "Thais",
            "{{TransportList|discount=no\n |{{TransportCell|Robson's Isle|100}}\n}}",
            "| geolabel     = Robson's Isle\n",
        )

        self.assertEqual([("Robson's Isle", 100, None)], [(d.name, d.price, d.origin) for d in npc.destinations])

    def test_npc_destinations_origin_legacy_transport_ignores_note(self):
        npc = self._parse_inline_npc("Venore", "{{Transport|Carlin, 110; From [[Thais]]}}")

        self.assertEqual([("Carlin", 110, "Venore")], [(d.name, d.price, d.origin) for d in npc.destinations])
