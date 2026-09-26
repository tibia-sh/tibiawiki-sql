"""Keep one issue listing the upstream commits that this copy's main branch lacks.

Run by `.github/workflows/upstream.yml` with the runner's Python, so it uses only the standard library.
"""
from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TITLE = "Upstream has new commits"
UPSTREAM = "https://github.com/Galarzaa90/tibiawiki-sql"
ISSUE_STATES = (None, "OPEN", "CLOSED")
TILDE_RUN = re.compile(r"~{3,}")
ZERO_WIDTH_SPACE = "\u200b"

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


def build_body(new_commits: list[str]) -> str:
    """Write the issue body, with the commit lines inside a ``~~~`` fence.

    Inside the fence, ``#12`` and ``@user`` render as plain text. A zero-width space goes between the tildes of any run
    of three or more in a subject, so no subject can close the fence.

    Args:
        new_commits: The upstream commits that main lacks, one ``<hash> <subject>`` line each.

    Returns:
        The issue body as Markdown.
    """
    lines = [TILDE_RUN.sub(lambda run: ZERO_WIDTH_SPACE.join(run.group()), commit) for commit in new_commits]
    return "\n".join([
        f"[Galarzaa90/tibiawiki-sql]({UPSTREAM}) `main` has {len(lines)} commit(s) that our `main` lacks:",
        "",
        "~~~",
        *lines,
        "~~~",
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
    """Pick the managed issue by its exact title.

    Args:
        issues: The issues from ``gh issue list --json number,title,state``.

    Returns:
        The managed issue, or ``None`` when there is none.

    Raises:
        ValueError: More than one issue has the title.
    """
    matches = [issue for issue in issues if issue["title"] == TITLE]
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
        "reopen": [["issue", "reopen", number], edit],
        "close": [["issue", "close", number]],
    }[action]


def main(argv: list[str]) -> None:
    """Read the commit list, look up the managed issue and bring it in line.

    Args:
        argv: The command-line arguments, the commit-list file's path only.

    Raises:
        SystemExit: The arguments are wrong or ``gh`` is not installed.
    """
    if len(argv) != 1:
        msg = "usage: upstream_check.py <commit-list file>"
        raise SystemExit(msg)
    gh = shutil.which("gh")
    if gh is None:
        msg = "gh is not installed"
        raise SystemExit(msg)
    new_commits = parse_commits(Path(argv[0]).read_text(encoding="utf-8", errors="replace"))
    listed = subprocess.run(  # noqa: S603 - fixed argument list, no shell
        [gh, "issue", "list", "--state", "all", "--author", "app/github-actions", "--json", "number,title,state"],
        check=True, capture_output=True, text=True,
    )
    issue = find_issue(json.loads(listed.stdout))
    action = decide(new_commits, issue["state"] if issue else None)
    log.info("%d new upstream commit(s), issue %s: %s", len(new_commits),
             f"#{issue['number']} {issue['state']}" if issue else "absent", action)
    with tempfile.TemporaryDirectory() as tmp:
        body_file = Path(tmp) / "body.md"
        body_file.write_text(build_body(new_commits), encoding="utf-8")
        for args in gh_commands(action, issue["number"] if issue else None, str(body_file)):
            subprocess.run([gh, *args], check=True)  # noqa: S603 - argument list, no shell, body passed as a file


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main(sys.argv[1:])
