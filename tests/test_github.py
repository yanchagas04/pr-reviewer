import json

import httpx
import pytest

from pr_reviewer import main as main_module
from pr_reviewer.github.client import GitHubClient
from pr_reviewer.github.comments import SUMMARY_MARKER, upsert_summary_comment
from pr_reviewer.github.events import load_pull_request_event


def write_event(tmp_path, head_name: str | None = "owner/repo"):
    head_repo = None if head_name is None else {"full_name": head_name}
    path = tmp_path / "event.json"
    path.write_text(
        json.dumps(
            {
                "pull_request": {
                    "number": 7,
                    "draft": False,
                    "head": {"sha": "a" * 40, "repo": head_repo},
                    "base": {"sha": "b" * 40, "repo": {"full_name": "owner/repo"}},
                }
            }
        )
    )
    return path


def comment(comment_id, body, user_type="Bot"):
    return {"id": comment_id, "body": body, "user": {"type": user_type}}


def fake_client(pages, calls):
    def handler(request):
        calls.append((request.method, request.url.path))
        if request.method != "GET":
            return httpx.Response(201, json={})
        page = int(request.url.params.get("page", 1))
        headers = {}
        if page < len(pages):
            next_url = request.url.copy_set_param("page", page + 1)
            headers["Link"] = f'<{next_url}>; rel="next"'
        return httpx.Response(200, json=pages[page - 1], headers=headers)

    return GitHubClient("token", "owner/repo", transport=httpx.MockTransport(handler))


@pytest.mark.parametrize(
    ("head_name", "is_fork"),
    [("owner/repo", False), ("someone/repo", True), (None, True)],
)
def test_event_detects_fork(tmp_path, head_name, is_fork):
    event = load_pull_request_event(write_event(tmp_path, head_name))
    assert (event.number, event.is_fork) == (7, is_fork)


def test_non_pull_request_event_is_rejected(tmp_path):
    path = tmp_path / "event.json"
    path.write_text("{}")
    with pytest.raises(ValueError):
        load_pull_request_event(path)


def test_upsert_creates_and_ignores_human_quoting_marker():
    calls = []
    with fake_client([[comment(1, SUMMARY_MARKER, "User")]], calls) as client:
        upsert_summary_comment(client, 7, "body")
    assert calls[-1] == ("POST", "/repos/owner/repo/issues/7/comments")


def test_upsert_updates_comment_found_on_second_page():
    calls = []
    pages = [[comment(1, None)], [comment(2, f"old {SUMMARY_MARKER}")]]
    with fake_client(pages, calls) as client:
        upsert_summary_comment(client, 7, "body")
    assert calls[-1] == ("PATCH", "/repos/owner/repo/issues/comments/2")


@pytest.mark.parametrize("is_fork", [True, False])
def test_forbidden_is_tolerated_only_for_forks(tmp_path, monkeypatch, is_fork):
    head = "someone/repo" if is_fork else "owner/repo"
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(write_event(tmp_path, head)))
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("GITHUB_TOKEN", "token")

    def forbidden(client, number, body):
        request = httpx.Request("POST", "https://api.github.com")
        raise httpx.HTTPStatusError(
            "forbidden", request=request, response=httpx.Response(403)
        )

    monkeypatch.setattr(main_module, "upsert_summary_comment", forbidden)

    if is_fork:
        main_module.main()
        assert "Revisão automática" in summary.read_text(encoding="utf-8")
    else:
        with pytest.raises(SystemExit):
            main_module.main()
