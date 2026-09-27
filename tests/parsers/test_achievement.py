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

    def _parse(self, content: str) -> Achievement:
        article = Article(
            article_id=1,
            title="Demonic Barkeeper",
            timestamp=datetime.datetime.fromisoformat("2018-08-20T04:33:15+00:00"),
            content=content,
        )

        return AchievementParser.from_article(article)

    def _edited(self, old: str, new: str) -> str:
        content = load_resource("content_achievement.txt")
        self.assertIn(old, content)
        return content.replace(old, new)

    def test_achievement_name_from_actualname(self):
        achievement = self._parse(self._edited(
            "| name          = Demonic Barkeeper\n",
            "| name          = Demonic Barkeeper (Achievement)\n| actualname    = Demonic Barkeeper\n",
        ))

        self.assertEqual("Demonic Barkeeper", achievement.name)

    def test_achievement_id_keeps_first_number(self):
        achievement = self._parse(self._edited("| achievementid = 111", "| achievementid = 12,345"))

        self.assertEqual(12, achievement.achievement_id)

    def test_achievement_name_without_actualname(self):
        achievement = self._parse(load_resource("content_achievement.txt"))

        self.assertEqual("Demonic Barkeeper", achievement.name)

    def test_achievement_description_cleaned(self):
        achievement = self._parse(self._edited("your demon blood", "your [[Demon|demon]] blood"))

        self.assertEqual(
            "Thick, red - shaken, not stirred - and with a straw in it: that's the way you prefer your demon blood. "
            "Served with an onion ring, the subtle metallic aftertaste is almost not noticeable. Beneficial effects on "
            "health or mana are welcome.",
            achievement.description,
        )
