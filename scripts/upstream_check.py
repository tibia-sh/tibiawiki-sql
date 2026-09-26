"""Keep one issue listing the upstream commits that this copy's main branch lacks.

Run by `.github/workflows/upstream.yml` with the runner's Python, so it uses only the standard library. The workflow
passes the compared base in ``BASE_REF`` (empty unless a manual run set ``base_ref``) and ``BASE_SHA`` (its short SHA).
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TITLE = "Upstream has new commits"
UPSTREAM = "https://github.com/Galarzaa90/tibiawiki-sql"
BOT_LOGIN = "app/github-actions"
LIST_ISSUES = [
    "issue", "list", "--state", "all", "--author", "github-actions[bot]", "--json", "number,title,state,author",
]
ISSUE_STATES = (None, "OPEN", "CLOSED")
MAX_LINE = 200
MAX_LINES = 300
ELLIPSIS = "\u2026"
CONTROL = re.compile(r"[\x00-\x08\x0a-\x1f\x7f-\x9f]")
TILDE_RUN = re.compile(r"~{3,}")
ZERO_WIDTH_SPACE = "\u200b"
SHORT_SHA = re.compile(r"[0-9a-f]{7,40}")
CODE_SPAN_SAFE = re.compile(r"[^`\s]+")

log = logging.getLogger(__name__)


def decide(new_commits: list[str], issue_state: str | None) -> str:
    """Choose what to do with the managed issue.

    Args:
        new_commits: The upstream commits that main lacks, one ``<hash> <subject>`` line each.
        issue_state: The managed issue's state, ``OPEN`` or ``CLOSED``, or ``None`` when there is no issue.

    Returns:
        ``create``, ``update``, ``reopen``, ``close`` or ``none``.

    Raises:
        ValueError: The issue state is not one of the known states.
    """
    if issue_state not in ISSUE_STATES:
        msg = f"unknown issue state: {issue_state!r}"
        raise ValueError(msg)
    if new_commits:
        return {None: "create", "OPEN": "update", "CLOSED": "reopen"}[issue_state]
    return "close" if issue_state == "OPEN" else "none"


def describe_base(base_ref: str, base_sha: str) -> str:
    """Name the base that upstream was compared with, as Markdown.

    Args:
        base_ref: The manual run's ``base_ref``, or ``""`` when the base is ``origin/main``.
        base_sha: The base's short SHA.

    Returns:
        ```main` at `<sha>``` or ```base_ref <ref>` at `<sha>```.

    Raises:
        ValueError: The SHA is not a lowercase hex SHA, or the ref would leave its code span.
    """
    if not SHORT_SHA.fullmatch(base_sha):
        msg = f"BASE_SHA must be a lowercase hex SHA, got {base_sha!r}"
        raise ValueError(msg)
    if not base_ref:
        return f"`main` at `{base_sha}`"
    if not CODE_SPAN_SAFE.fullmatch(base_ref):
        msg = f"BASE_REF must hold no backticks or whitespace, got {base_ref!r}"
        raise ValueError(msg)
    return f"`base_ref {base_ref}` at `{base_sha}`"


def _commit_line(commit: str) -> str:
    """Make one commit line inert and bounded: no control characters, no tilde run, at most ``MAX_LINE`` characters.

    Tildes are split before the cut, and the cut only drops a suffix, so it can't rejoin a run.

    Args:
        commit: One ``<hash> <subject>`` line from git.

    Returns:
        The line to put inside the fence.
    """
    line = TILDE_RUN.sub(lambda run: ZERO_WIDTH_SPACE.join(run.group()), CONTROL.sub("", commit))
    return line if len(line) <= MAX_LINE else line[:MAX_LINE - 1] + ELLIPSIS


def build_body(new_commits: list[str], base: str) -> str:
    """Write the issue body, with the commit lines inside a ``~~~`` fence.

    Inside the fence, ``#12`` and ``@user`` render as plain text. Each line loses its control characters other than
    tab, gets a zero-width space between the tildes of any run of three or more, so no subject can close the fence, and
    is cut to ``MAX_LINE`` characters. The fence holds at most ``MAX_LINES`` lines, which keeps the body well under
    GitHub's 65,536-character limit.

    Args:
        new_commits: The upstream commits that main lacks, one ``<hash> <subject>`` line each.
        base: The compared base, from :func:`describe_base`.

    Returns:
        The issue body as Markdown.
    """
    lines = [_commit_line(commit) for commit in new_commits[:MAX_LINES]]
    more = len(new_commits) - len(lines)
    rest = [f"... and {more} more commit{'s' if more > 1 else ''}"] if more else []
    return "\n".join([
        f"[Galarzaa90/tibiawiki-sql]({UPSTREAM}) `main` has {len(new_commits)} commit(s) that our `main` lacks.",
        "",
        f"Compared with {base}.",
        "",
        "~~~",
        *lines,
        "~~~",
        *rest,
        "",
        'To merge them, see "About this copy" in README.md. This issue closes itself once `main` has them all.',
        "",
    ])


def parse_commits(text: str) -> list[str]:
    """Read the ``git log --format='%h %s'`` output, skipping blank lines.

    Args:
        text: The contents of the commit-list file.

    Returns:
        One ``<hash> <subject>`` line per commit.
    """
    return [line for line in text.split("\n") if line.strip()]


def find_issue(issues: list[dict]) -> dict | None:
    """Pick the managed issue by its exact title and the Actions bot as its author.

    ``LIST_ISSUES`` already asks gh for the bot's issues only. An issue with the title by anyone else means gh's author
    filter changed, so it fails instead of creating a second issue.

    Args:
        issues: The issues from ``LIST_ISSUES``.

    Returns:
        The managed issue, or ``None`` when there is none.

    Raises:
        ValueError: An issue with the title has another author, or more than one issue has the title.
    """
    matches = [issue for issue in issues if issue["title"] == TITLE]
    for issue in matches:
        author = issue["author"]
        if author.get("is_bot") is not True or author.get("login") != BOT_LOGIN:
            msg = f"issue #{issue['number']} is titled {TITLE!r} but its author is {author!r}, not {BOT_LOGIN}"
            raise ValueError(msg)
    if len(matches) > 1:
        numbers = ", ".join(f"#{issue['number']}" for issue in matches)
        msg = f"more than one issue is titled {TITLE!r}: {numbers}"
        raise ValueError(msg)
    return matches[0] if matches else None


def gh_commands(action: str, issue_number: int | None, body_file: str) -> list[list[str]]:
    """List the ``gh`` arguments that carry out an action.

    Args:
        action: What :func:`decide` chose.
        issue_number: The managed issue's number, ``None`` when there is no issue.
        body_file: The path of the file holding the issue body.

    Returns:
        One argument list per ``gh`` call, without the ``gh`` executable.

    Raises:
        ValueError: The action is unknown, or it acts on an issue and no number is given.
    """
    if action == "none":
        return []
    if action == "create":
        return [["issue", "create", "--title", TITLE, "--body-file", body_file]]
    if action not in {"update", "reopen", "close"}:
        msg = f"unknown action: {action!r}"
        raise ValueError(msg)
    if issue_number is None:
        msg = f"{action} needs an issue number"
        raise ValueError(msg)
    number = str(issue_number)
    edit = ["issue", "edit", number, "--body-file", body_file]
    return {
        "update": [edit],
        "reopen": [edit, ["issue", "reopen", number]],
        "close": [["issue", "close", number]],
    }[action]


def main(argv: list[str]) -> None:
    """Read the commit list, look up the managed issue and bring it in line.

    Args:
        argv: The command-line arguments, the commit-list file's path only.

    Raises:
        SystemExit: The arguments are wrong or ``gh`` is not installed.
    """
    base = describe_base(os.environ.get("BASE_REF", ""), os.environ.get("BASE_SHA", ""))
    if len(argv) != 1:
        msg = "usage: upstream_check.py <commit-list file>"
        raise SystemExit(msg)
    gh = shutil.which("gh")
    if gh is None:
        msg = "gh is not installed"
        raise SystemExit(msg)
    new_commits = parse_commits(Path(argv[0]).read_text(encoding="utf-8", errors="replace"))
    listed = subprocess.run([gh, *LIST_ISSUES], check=True, capture_output=True, text=True)  # noqa: S603 - fixed list
    issue = find_issue(json.loads(listed.stdout))
    action = decide(new_commits, issue["state"] if issue else None)
    log.info("%d new upstream commit(s), issue %s: %s", len(new_commits),
             f"#{issue['number']} {issue['state']}" if issue else "absent", action)
    with tempfile.TemporaryDirectory() as tmp:
        body_file = Path(tmp) / "body.md"
        body_file.write_text(build_body(new_commits, base), encoding="utf-8")
        for args in gh_commands(action, issue["number"] if issue else None, str(body_file)):
            subprocess.run([gh, *args], check=True)  # noqa: S603 - argument list, no shell, body passed as a file


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main(sys.argv[1:])
