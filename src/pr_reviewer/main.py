"""Ponto de entrada da Action."""

import os
import sys
from pathlib import Path

import httpx

from pr_reviewer.github.client import GitHubClient
from pr_reviewer.github.comments import upsert_summary_comment
from pr_reviewer.github.events import PullRequestEvent, load_pull_request_event


def render_hello(event: PullRequestEvent) -> str:
    yes_no = {True: "sim", False: "não"}
    return (
        "## Revisão automática do PR\n\n"
        "Hello! O agente está instalado, mas a análise ainda não foi "
        "implementada.\n\n"
        f"**PR:** #{event.number} · **Commit:** {event.head_sha[:7]} · "
        f"**Draft:** {yes_no[event.is_draft]} · **Fork:** {yes_no[event.is_fork]}"
    )


def write_job_summary(body: str) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with Path(path).open("a", encoding="utf-8") as file:
            file.write(f"{body}\n")


def run() -> None:
    event = load_pull_request_event(os.environ["GITHUB_EVENT_PATH"])
    body = render_hello(event)

    with GitHubClient(
        token=os.environ["GITHUB_TOKEN"],
        repository=os.environ["GITHUB_REPOSITORY"],
        api_url=os.environ.get("GITHUB_API_URL", "https://api.github.com"),
    ) as client:
        try:
            upsert_summary_comment(client, event.number, body)
        except httpx.HTTPStatusError as error:
            # Em PRs de fork o GITHUB_TOKEN é somente leitura.
            if not (event.is_fork and error.response.status_code == 403):
                raise
            print("::warning::PR de fork: sem permissão para comentar no PR.")
            write_job_summary(body)
            return
    print(f"Comentário publicado no PR #{event.number}.")


def main() -> None:
    try:
        run()
    except (KeyError, ValueError, OSError, httpx.HTTPError) as error:
        print(f"::error::pr-reviewer falhou: {error!r}")
        sys.exit(1)
