import re
import unittest

from scripts.upstream_check import TITLE, build_body, decide, find_issue, gh_commands, parse_commits

COMMITS = ["abc1234 Fix creature parsing", "def5678 Add mounts"]
FENCE = re.compile(r"^ {0,3}(~{3,}|`{3,})")


class TestDecide(unittest.TestCase):
    def test_commits_without_issue_creates(self):
        self.assertEqual("create", decide(COMMITS, None))

    def test_commits_with_open_issue_updates(self):
        self.assertEqual("update", decide(COMMITS, "OPEN"))

    def test_commits_with_closed_issue_reopens(self):
        self.assertEqual("reopen", decide(COMMITS, "CLOSED"))

    def test_no_commits_with_open_issue_closes(self):
        self.assertEqual("close", decide([], "OPEN"))

    def test_no_commits_without_issue_does_nothing(self):
        self.assertEqual("none", decide([], None))

    def test_no_commits_with_closed_issue_does_nothing(self):
        self.assertEqual("none", decide([], "CLOSED"))

    def test_unknown_issue_state_is_rejected(self):
        with self.assertRaises(ValueError):
            decide(COMMITS, "MERGED")


class TestBuildBody(unittest.TestCase):
    def test_lists_every_commit_inside_one_fence(self):
        body = build_body(COMMITS)
        lines = body.splitlines()
        fences = [i for i, line in enumerate(lines) if FENCE.match(line)]
        self.assertEqual(2, len(fences))
        self.assertEqual("~~~", lines[fences[0]])
        self.assertEqual("~~~", lines[fences[1]])
        self.assertEqual(COMMITS, lines[fences[0] + 1:fences[1]])

    def test_hostile_subject_stays_inert(self):
        subject = "abc1234 Close #12 ~~~ ping @user ~~~~ `` ```"
        body = build_body([subject, "def5678 ~~~"])
        lines = body.splitlines()
        fences = [i for i, line in enumerate(lines) if FENCE.match(line)]
        self.assertEqual(2, len(fences))
        self.assertEqual(2, body.count("~~~"))
        inside = lines[fences[0] + 1:fences[1]]
        self.assertEqual(2, len(inside))
        self.assertIn("#12", inside[0])
        self.assertIn("@user", inside[0])
        outside = "\n".join(lines[:fences[0]] + lines[fences[1] + 1:])
        self.assertNotIn("#12", outside)
        self.assertNotIn("@user", outside)

    def test_subject_split_by_carriage_return_cannot_close_the_fence(self):
        body = build_body(["abc1234 first\r~~~\r#12 @user"])
        lines = body.splitlines()
        fences = [i for i, line in enumerate(lines) if FENCE.match(line)]
        self.assertEqual(2, len(fences))
        self.assertEqual(2, body.count("~~~"))


class TestParseCommits(unittest.TestCase):
    def test_skips_blank_lines(self):
        self.assertEqual(COMMITS, parse_commits("abc1234 Fix creature parsing\n\ndef5678 Add mounts\n"))

    def test_empty_file_has_no_commits(self):
        self.assertEqual([], parse_commits(""))


class TestFindIssue(unittest.TestCase):
    def test_matches_exact_title_only(self):
        issues = [
            {"number": 1, "title": TITLE + "!", "state": "OPEN"},
            {"number": 2, "title": TITLE.lower(), "state": "OPEN"},
            {"number": 3, "title": TITLE, "state": "CLOSED"},
        ]
        self.assertEqual({"number": 3, "title": TITLE, "state": "CLOSED"}, find_issue(issues))

    def test_no_match_is_none(self):
        self.assertIsNone(find_issue([{"number": 1, "title": "Other", "state": "OPEN"}]))

    def test_two_matches_are_rejected(self):
        issues = [
            {"number": 1, "title": TITLE, "state": "OPEN"},
            {"number": 2, "title": TITLE, "state": "CLOSED"},
        ]
        with self.assertRaises(ValueError):
            find_issue(issues)


class TestGhCommands(unittest.TestCase):
    def test_create(self):
        self.assertEqual(
            [["issue", "create", "--title", TITLE, "--body-file", "body.md"]],
            gh_commands("create", None, "body.md"),
        )

    def test_update(self):
        self.assertEqual([["issue", "edit", "7", "--body-file", "body.md"]], gh_commands("update", 7, "body.md"))

    def test_reopen_also_updates(self):
        self.assertEqual(
            [["issue", "reopen", "7"], ["issue", "edit", "7", "--body-file", "body.md"]],
            gh_commands("reopen", 7, "body.md"),
        )

    def test_close(self):
        self.assertEqual([["issue", "close", "7"]], gh_commands("close", 7, "body.md"))

    def test_none(self):
        self.assertEqual([], gh_commands("none", None, "body.md"))

    def test_action_on_an_issue_needs_its_number(self):
        with self.assertRaises(ValueError):
            gh_commands("update", None, "body.md")


if __name__ == "__main__":
    unittest.main()
