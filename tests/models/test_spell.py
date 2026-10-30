import datetime
import sqlite3
import unittest

from tests import load_resource
from tibiawikisql import schema
from tibiawikisql.api import Article
from tibiawikisql.models import Spell
from tibiawikisql.parsers import SpellParser


class TestSpell(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        schema.create_tables(self.conn)

    def _round_trip(self, title: str, resource: str) -> Spell:
        article = Article(
            article_id=1,
            title=title,
            timestamp=datetime.datetime.fromisoformat("2026-08-06T21:35:46+00:00"),
            content=load_resource(resource),
        )
        SpellParser.from_article(article).insert(self.conn)

        return Spell.get_one_by_field(self.conn, "article_id", 1)

    def test_spell_id_round_trip(self):
        loaded = self._round_trip("Flame Strike", "content_spell.txt")

        self.assertEqual(89, loaded.spell_id)

    def test_spell_id_round_trip_none(self):
        loaded = self._round_trip("Second Wind", "content_spell_second_wind.txt")

        self.assertIsNone(loaded.spell_id)
