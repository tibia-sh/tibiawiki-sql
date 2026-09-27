# Changed by tibia.sh in 2026. See "About this copy" in README.md.
import datetime
import sqlite3
import unittest

from tests import load_resource
from tibiawikisql.api import Article
from tibiawikisql.models import Achievement
from tibiawikisql.parsers import AchievementParser
from tibiawikisql.schema import AchievementTable


class TestAchievementParser(unittest.TestCase):

    def test_achievement_parser_from_article(self):
        article = Article(
            article_id=1,
            title="Demonic Barkeeper",
            timestamp=datetime.datetime.fromisoformat("2018-08-20T04:33:15+00:00"),
            content=load_resource("content_achievement.txt"),
        )

        achievement = AchievementParser.from_article(article)

        self.assertIsInstance(achievement, Achievement)

    def test_unknown_achievement(self):
        article = Article(
            article_id=1,
            title="Achievement 563",
            timestamp=datetime.datetime.fromisoformat("2026-08-06T21:35:46+00:00"),
            content=load_resource("content_achievement_563.txt"),
        )

        achievement = AchievementParser.from_article(article)

        self.assertIsNone(achievement.name)
        self.assertIsNone(achievement.description)
        self.assertEqual(563, achievement.achievement_id)
        self.assertIs(True, achievement.is_secret)

        conn = sqlite3.connect(":memory:")
        self.addCleanup(conn.close)
        conn.executescript(AchievementTable.get_create_table_statement())
        achievement.insert(conn)
        stored = conn.execute("SELECT name, description FROM achievement WHERE article_id = 1").fetchone()
        self.assertEqual((None, None), stored)
