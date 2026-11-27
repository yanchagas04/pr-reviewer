"""Cliente mínimo da API REST do GitHub."""

from collections.abc import Iterator
from typing import Any

import httpx


class GitHubClient:
    def __init__(
        self,
        token: str,
        repository: str,
        api_url: str = "https://api.github.com",
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._repo = f"/repos/{repository}"
        self._http = httpx.Client(
            base_url=api_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "pr-reviewer",
            },
            timeout=30,
            transport=transport,
        )

    def __enter__(self) -> "GitHubClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self._http.close()

    def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        response = self._http.request(method, url, **kwargs)
        response.raise_for_status()
        return response

    def list_issue_comments(self, number: int) -> Iterator[dict[str, Any]]:
        url: str | None = f"{self._repo}/issues/{number}/comments?per_page=100"
        while url:
            response = self._request("GET", url)
            yield from response.json()
            url = response.links.get("next", {}).get("url")

    def create_issue_comment(self, number: int, body: str) -> None:
        self._request(
            "POST", f"{self._repo}/issues/{number}/comments", json={"body": body}
        )

    def update_issue_comment(self, comment_id: int, body: str) -> None:
        self._request(
            "PATCH", f"{self._repo}/issues/comments/{comment_id}", json={"body": body}
        )
