"""论坛子系统边界与异常补充测试"""
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
    assert response.status_code < 400, f"HTTP {response.status_code}: {response.text}"
    body = response.json()
    assert body["code"] == 0, f"业务错误: {body.get('message')}"
    return body["data"]


# ==================== 一、输入边界测试 ====================

class TestInputBoundary:
    """超长内容、特殊字符、边界值"""

    def test_very_long_title(self, client):
        """超长标题（10000字符）"""
        long_title = "测" * 10000
        resp = client.post(
            "/api/v1/forum/posts",
            json={
                "board_id": 10,
                "module": "discussion",
                "title": long_title,
                "content": "正常内容",
            },
            headers={"X-User-Id": "7", "X-User-Role": "student"},
        )
        # 不崩溃即可：可能拒绝（400）或截断（200）
        assert resp.status_code < 500

    def test_very_long_content(self, client):
        """超长内容（50000字符）"""
        long_content = "内" * 50000
        resp = client.post(
            "/api/v1/forum/posts",
            json={
                "board_id": 10,
                "module": "discussion",
                "title": "正常标题",
                "content": long_content,
            },
            headers={"X-User-Id": "7", "X-User-Role": "student"},
        )
        assert resp.status_code < 500

    def test_special_characters_in_title(self, client):
        """标题含特殊字符：emoji + HTML标签"""
        resp = client.post(
            "/api/v1/forum/posts",
            json={
                "board_id": 10,
                "module": "discussion",
                "title": "🎉测试 <script>alert('xss')</script> <!-- comment -->",
                "content": "特殊字符测试内容",
            },
            headers={"X-User-Id": "7", "X-User-Role": "student"},
        )
        # 不崩溃即可
        assert resp.status_code < 500

    def test_html_in_content(self, client):
        """内容含 HTML 标签"""
        resp = client.post(
            "/api/v1/forum/posts",
            json={
                "board_id": 10,
                "module": "discussion",
                "title": "HTML测试",
                "content": "<b>粗体</b><img src=x onerror=alert(1)>",
            },
            headers={"X-User-Id": "7", "X-User-Role": "student"},
        )
        assert resp.status_code < 500

    def test_sql_injection_attempt(self, client):
        """SQL 注入尝试"""
        resp = client.post(
            "/api/v1/forum/posts",
            json={
                "board_id": 10,
                "module": "discussion",
                "title": "'; DROP TABLE posts; --",
                "content": "注入测试",
            },
            headers={"X-User-Id": "7", "X-User-Role": "student"},
        )
        assert resp.status_code < 500


# ==================== 二、异常场景测试 ====================

class TestExceptionScenarios:
    """异常操作与错误处理"""

    def test_post_to_nonexistent_board(self, client):
        """向不存在的板块发帖"""
        resp = client.post(
            "/api/v1/forum/posts",
            json={
                "board_id": 99999,
                "module": "discussion",
                "title": "不存在板块",
                "content": "测试内容",
            },
            headers={"X-User-Id": "7", "X-User-Role": "student"},
        )
        # 应该返回错误
        assert resp.status_code >= 400 or resp.json()["code"] != 0

    def test_reply_to_nonexistent_post(self, client):
        """回复不存在的帖子"""
        resp = client.post(
            "/api/v1/forum/posts/99999/replies",
            json={"content": "回复不存在帖"},
            headers={"X-User-Id": "7", "X-User-Role": "student"},
        )
        assert resp.status_code == 404

    def test_update_nonexistent_post(self, client):
        """修改不存在的帖子"""
        resp = client.put(
            "/api/v1/forum/posts/99999",
            json={"title": "修改不存在"},
            headers={"X-User-Id": "7", "X-User-Role": "student"},
        )
        assert resp.status_code == 404

    def test_delete_nonexistent_post(self, client):
        """删除不存在的帖子"""
        resp = client.delete(
            "/api/v1/forum/posts/99999",
            headers={"X-User-Id": "7", "X-User-Role": "student"},
        )
        assert resp.status_code == 404

    def test_duplicate_announcement_title(self, client):
        """重复标题公告（不禁止，验证不崩溃）"""
        for i in range(2):
            resp = client.post(
                "/api/v1/forum/announcements",
                json={
                    "board_id": 10,
                    "title": "重复标题公告",
                    "content": f"内容{i}",
                },
                headers={"X-User-Id": "2", "X-User-Role": "teacher"},
            )
            assert resp.status_code < 500

    def test_get_nonexistent_attachment(self, client):
        """查看不存在帖子的附件列表"""
        resp = client.get("/api/v1/forum/posts/99999/attachments")
        assert resp.status_code == 404


# ==================== 三、分页边界测试 ====================

class TestPaginationBoundary:
    """分页参数边界"""

    def test_page_size_too_large(self, client):
        """page_size 超大值"""
        resp = client.get("/api/v1/forum/posts", params={"page": 1, "page_size": 10000})
        assert resp.status_code < 500

    def test_page_zero(self, client):
        """page=0"""
        resp = client.get("/api/v1/forum/posts", params={"page": 0, "page_size": 10})
        assert resp.status_code < 500

    def test_search_special_chars(self, client):
        """搜索特殊字符"""
        resp = client.get(
            "/api/v1/forum/search/posts",
            params={"keyword": "🎉%' OR 1=1 --", "page": 1, "page_size": 10},
        )
        assert resp.status_code < 500


# ==================== 四、并发基础测试 ====================

class TestBasicConcurrency:
    """基础并发请求"""

    def test_concurrent_post_creation(self, client):
        """快速连续发帖 10 次"""
        created_ids = []
        for i in range(10):
            resp = client.post(
                "/api/v1/forum/posts",
                json={
                    "board_id": 10,
                    "module": "discussion",
                    "title": f"并发帖{i}",
                    "content": f"并发内容{i}",
                },
                headers={"X-User-Id": "7", "X-User-Role": "student"},
            )
            assert resp.status_code < 500
            if resp.status_code == 200:
                created_ids.append(resp.json()["data"]["id"])

        # 验证所有帖子都可查到
        for pid in created_ids:
            get_resp = client.get(f"/api/v1/forum/posts/{pid}")
            assert get_resp.status_code == 200
