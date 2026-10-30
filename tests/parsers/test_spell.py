import datetime
import unittest

from tests import load_resource
from tibiawikisql.api import Article
from tibiawikisql.models import Spell
from tibiawikisql.parsers import SpellParser
from tibiawikisql.utils import parse_whole_number

SNIPER_CONTENT = """{{Infobox Spell|List={{{1|}}}|GetValue={{{GetValue|}}}
| name           = Sniper
| spellid        =
| words          = utori con
| mana           = 250
| type           = Instant
| subclass       = Support
| secondarygroup = Stance
| levelrequired  = 20
| premium        = yes
| voc            = [[Paladin]]s.
| soul           = 0
| cooldown       = 10
| cooldowngroup  = 2
| cooldowngroup2 = 10
| libraryname    = sniper
| implemented    =
| status         = ts-only
}}"""

MANA_VARIES_CONTENT = """{{Infobox Spell|List={{{1|}}}|GetValue={{{GetValue|}}}
| name           = Train Party
| type           = Instant
| subclass       = Support
| words          = utito mas sio
| mana           = Varies
| cooldown       = 2
| levelrequired  = 32
| voc            = [[Knight]]s
| effect         = Increases the skills of the party members.
}}"""


class TestSpellParserMissingFields(unittest.TestCase):
    def _parse(self, title: str, content: str) -> Spell:
        article = Article(
            article_id=1,
            title=title,
            timestamp=datetime.datetime.fromisoformat("2026-08-06T21:35:46+00:00"),
            content=content,
        )

        return SpellParser.from_article(article)

    def test_ultimate_explosion_without_whole_cooldown(self):
        spell = self._parse("Ultimate Explosion", load_resource("content_spell_ultimate_explosion.txt"))

        self.assertIsNone(spell.cooldown)
        self.assertEqual(1200, spell.mana)
        self.assertEqual("Instant", spell.spell_type)

    def test_second_wind_without_mana(self):
        spell = self._parse("Second Wind", load_resource("content_spell_second_wind.txt"))

        self.assertEqual(0, spell.mana)
        self.assertEqual(120, spell.cooldown)

    def test_mana_varies_stays_zero(self):
        spell = self._parse("Train Party", MANA_VARIES_CONTENT)

        self.assertEqual(0, spell.mana)

    def test_broadcast_without_type_subclass_level_or_cooldown(self):
        spell = self._parse("Broadcast", load_resource("content_spell_broadcast.txt"))

        self.assertIsNone(spell.spell_type)
        self.assertIsNone(spell.group_spell)
        self.assertIsNone(spell.level)
        self.assertIsNone(spell.cooldown)
        self.assertEqual(90, spell.mana)

    def test_sniper_without_effect(self):
        spell = self._parse("Sniper", SNIPER_CONTENT)

        self.assertIsNone(spell.effect)


class TestSpellParserSpellId(unittest.TestCase):
    def _parse(self, title: str, content: str) -> Spell:
        article = Article(
            article_id=1,
            title=title,
            timestamp=datetime.datetime.fromisoformat("2026-08-06T21:35:46+00:00"),
            content=content,
        )

        return SpellParser.from_article(article)

    def _edited(self, old: str, new: str) -> Spell:
        content = load_resource("content_spell.txt")
        self.assertIn(old, content)
        return self._parse("Flame Strike", content.replace(old, new))

    def test_flame_strike(self):
        spell = self._parse("Flame Strike", load_resource("content_spell.txt"))

        self.assertEqual(89, spell.spell_id)

    def test_ultimate_explosion(self):
        spell = self._parse("Ultimate Explosion", load_resource("content_spell_ultimate_explosion.txt"))

        self.assertEqual(24, spell.spell_id)

    def test_second_wind_empty(self):
        spell = self._parse("Second Wind", load_resource("content_spell_second_wind.txt"))

        self.assertIsNone(spell.spell_id)

    def test_absent(self):
        spell = self._parse("Train Party", MANA_VARIES_CONTENT)

        self.assertIsNone(spell.spell_id)

    def test_unknown(self):
        spell = self._edited("| spellid       = 89", "| spellid       = ?")

        self.assertIsNone(spell.spell_id)

    def test_ignores_a_trailing_comment(self):
        spell = self._edited("| spellid       = 89", "| spellid       = 89 <!-- 90 -->")

        self.assertEqual(89, spell.spell_id)

    def test_only_in_a_comment(self):
        spell = self._edited("| spellid       = 89", "| spellid       = <!-- 89 -->")

        self.assertIsNone(spell.spell_id)


class TestParseWholeNumber(unittest.TestCase):
    def test_parse_whole_number(self):
        self.assertEqual(4, parse_whole_number("4"))
        self.assertEqual(12, parse_whole_number(" 12 "))
        self.assertIsNone(parse_whole_number("1-2s"))
        self.assertIsNone(parse_whole_number(""))
        self.assertIsNone(parse_whole_number("2s"))
