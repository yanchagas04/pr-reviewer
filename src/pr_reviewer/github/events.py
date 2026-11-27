"""Leitura do evento que disparou a Action."""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PullRequestEvent:
    number: int
    head_sha: str
    base_sha: str
    is_draft: bool
    is_fork: bool


def load_pull_request_event(path: str | Path) -> PullRequestEvent:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    pr = payload.get("pull_request")
    if pr is None:
        raise ValueError("o evento não é de pull_request")

    # head.repo vem nulo quando o fork foi apagado.
    head_repo = pr["head"].get("repo")
    return PullRequestEvent(
        number=pr["number"],
        head_sha=pr["head"]["sha"],
        base_sha=pr["base"]["sha"],
        is_draft=pr.get("draft", False),
        is_fork=head_repo is None
        or head_repo["full_name"] != pr["base"]["repo"]["full_name"],
    )
