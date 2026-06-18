from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.database import get_session
from app.main import app
from app.seed import seed_forum_boards


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        seed_forum_boards(session)

    def override_get_session() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def unwrap(response):
    assert response.status_code < 400, response.text
    body = response.json()
    assert body["code"] == 0
    return body["data"]


def test_create_post_reply_search_and_stats(client: TestClient) -> None:
    created = unwrap(
        client.post(
            "/api/v1/forum/posts",
            json={
                "board_id": 10,
                "module": "discussion",
                "title": "接口字段对齐",
                "content": "讨论论坛交流子系统接口字段和分页格式。",
            },
            headers={"X-User-Id": "7", "X-User-Role": "student", "X-User-Name": "student7"},
        )
    )

    assert created["course_id"] == "SE-2026"

    reply = unwrap(
        client.post(
            f"/api/v1/forum/posts/{created['id']}/replies",
            json={"content": "分页使用 items + pagination。"},
            headers={"X-User-Id": "8", "X-User-Role": "teacher", "X-User-Name": "teacher8"},
        )
    )
    assert reply["floor"] == 1

    replies = unwrap(
        client.get(f"/api/v1/forum/posts/{created['id']}/replies", params={"view": "tree"})
    )
    assert len(replies["items"]) == 1

    search = unwrap(
        client.get(
            "/api/v1/forum/search/posts",
            params={"keyword": "分页", "page": 1, "page_size": 10},
        )
    )
    assert search["pagination"]["total"] == 1

    stats = unwrap(client.get("/api/v1/forum/stats/user_activity", params={"period": "week"}))
    assert stats["items"]


def test_announcements_lifecycle(client: TestClient) -> None:
    created = unwrap(
        client.post(
            "/api/v1/forum/announcements",
            json={"board_id": 10, "title": "提交提醒", "content": "请按时提交材料", "popup": True},
            headers={"X-User-Id": "2", "X-User-Role": "teacher"},
        )
    )
    toggled = unwrap(client.put(f"/api/v1/forum/announcements/{created['id']}/popup_toggle"))
    assert toggled["popup"] is False

    updated = unwrap(
        client.put(
            f"/api/v1/forum/announcements/{created['id']}",
            json={"pinned": True, "status": "published"},
            headers={"X-User-Id": "2", "X-User-Role": "teacher"},
        )
    )
    assert updated["pinned"] is True

    data = unwrap(client.get("/api/v1/forum/announcements", params={"page": 1, "page_size": 10}))
    assert data["pagination"]["total"] >= 1


def test_board_and_moderation_support(client: TestClient) -> None:
    boards = unwrap(client.get("/api/v1/forum/boards", params={"page": 1, "page_size": 10}))
    assert boards["items"][0]["course_name"]

    created_board = unwrap(
        client.post(
            "/api/v1/forum/boards",
            json={
                "course_id": "MATH-1",
                "course_name": "Advanced Math",
                "title": "Advanced Math Forum",
                "description": "Discussion board",
                "status": "active",
            },
            headers={"X-User-Role": "teacher"},
        )
    )
    assert created_board["course_id"] == "MATH-1"

    updated_board = unwrap(
        client.put(
            f"/api/v1/forum/boards/{created_board['id']}",
            json={"status": "inactive", "popup_enabled": True},
            headers={"X-User-Role": "teacher"},
        )
    )
    assert updated_board["status"] == "inactive"
    assert updated_board["popup_enabled"] is True

    created_post = unwrap(
        client.post(
            "/api/v1/forum/posts",
            json={
                "board_id": 10,
                "module": "general",
                "title": "Moderation target",
                "content": "Needs review",
            },
            headers={"X-User-Id": "11", "X-User-Role": "student", "X-User-Name": "student11"},
        )
    )
    report = unwrap(
        client.post(
            "/api/v1/forum/moderation/reports",
            json={"target_type": "post", "target_id": created_post["id"], "reason": "review"},
        )
    )
    assert report["status"] == "pending"

    handled = unwrap(
        client.put(
            f"/api/v1/forum/moderation/{report['id']}/handle",
            json={"status": "hidden", "reason": "hidden by admin"},
            headers={"X-User-Id": "1", "X-User-Role": "admin", "X-User-Name": "admin"},
        )
    )
    assert handled["status"] == "hidden"

    moderation_list = unwrap(client.get("/api/v1/forum/moderation", params={"status": "hidden"}))
    assert moderation_list["pagination"]["total"] >= 1
