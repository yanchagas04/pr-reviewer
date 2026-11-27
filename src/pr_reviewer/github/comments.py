"""Comentário de resumo, único por PR."""

from pr_reviewer.github.client import GitHubClient

SUMMARY_MARKER = "<!-- pr-reviewer:summary -->"


def upsert_summary_comment(client: GitHubClient, number: int, body: str) -> None:
    """Cria o comentário de resumo ou atualiza o já existente."""
    body = f"{body}\n\n{SUMMARY_MARKER}"
    for comment in client.list_issue_comments(number):
        # Só comentários de bot: uma pessoa pode ter citado o marcador.
        if comment["user"]["type"] == "Bot" and SUMMARY_MARKER in (
            comment["body"] or ""
        ):
            client.update_issue_comment(comment["id"], body)
            return
    client.create_issue_comment(number, body)
