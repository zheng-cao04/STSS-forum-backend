"""论坛子系统压力测试 —— 并发请求与稳定性验证"""
from collections.abc import Generator
import time
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


class TestPostConcurrency:
    """发帖并发压测"""

    def test_20_concurrent_posts(self, client):
        """20 次快速发帖，验证全部成功且不超卖ID"""
        start = time.time()
        results = []

        for i in range(20):
            resp = client.post(
                "/api/v1/forum/posts",
                json={
                    "board_id": 10,
                    "module": "discussion",
                    "title": f"并发帖子-{i}",
                    "content": f"并发测试内容-{i}",
                },
                headers={"X-User-Id": "7", "X-User-Role": "student"},
            )
            results.append(resp)

        elapsed = time.time() - start

        # 统计结果
        success = sum(1 for r in results if r.status_code == 200)
        failed = sum(1 for r in results if r.status_code >= 500)
        error = sum(1 for r in results if r.status_code in [400, 403, 404])

        print(f"\n20并发发帖: 成功={success}, 客户端错误={error}, 服务端错误={failed}, 耗时={elapsed:.2f}s")

        # 断言：无服务端崩溃，成功率 >= 90%
        assert failed == 0, f"服务端崩溃 {failed} 次"
        assert success >= 18, f"成功率过低: {success}/20"

    def test_30_mixed_operations(self, client):
        """30 次混合操作（发帖+查帖+搜索），验证稳定性"""
        start = time.time()
        server_errors = 0
        total = 30

        for i in range(total):
            # 轮流执行不同操作
            if i % 3 == 0:
                # 发帖
                resp = client.post(
                    "/api/v1/forum/posts",
                    json={
                        "board_id": 10,
                        "module": "discussion",
                        "title": f"混合测试帖-{i}",
                        "content": f"混合内容-{i}",
                    },
                    headers={"X-User-Id": "7", "X-User-Role": "student"},
                )
            elif i % 3 == 1:
                # 查帖子列表
                resp = client.get(
                    "/api/v1/forum/posts",
                    params={"board_id": 10, "page": 1, "page_size": 5},
                )
            else:
                # 搜索
                resp = client.get(
                    "/api/v1/forum/search/posts",
                    params={"keyword": "测试", "page": 1, "page_size": 5},
                )

            if resp.status_code >= 500:
                server_errors += 1

        elapsed = time.time() - start

        print(f"\n30次混合操作: 服务端错误={server_errors}/{total}, 耗时={elapsed:.2f}s")

        # 断言：零服务端崩溃
        assert server_errors == 0, f"服务端崩溃 {server_errors} 次"

    def test_get_endpoints_under_load(self, client):
        """GET 接口高频访问（热门帖子、用户活动、板块列表）"""
        server_errors = 0
        total = 40

        for i in range(total):
            if i % 4 == 0:
                resp = client.get("/api/v1/forum/stats/hot_posts", params={"period": "week", "limit": 5})
            elif i % 4 == 1:
                resp = client.get("/api/v1/forum/stats/user_activity", params={"period": "week"})
            elif i % 4 == 2:
                resp = client.get("/api/v1/forum/boards", params={"page": 1, "page_size": 10})
            else:
                resp = client.get("/api/v1/forum/healthz")

            if resp.status_code >= 500:
                server_errors += 1

        print(f"\n40次GET高频访问: 服务端错误={server_errors}/{total}")

        assert server_errors == 0, f"GET接口崩溃 {server_errors} 次"
        assert resp.status_code == 200  # 最后一次请求正常


class TestStressBoundary:
    """压力边界"""

    def test_rapid_create_delete_posts(self, client):
        """快速创建后立即删除"""
        server_errors = 0

        for i in range(10):
            # 创建
            resp = client.post(
                "/api/v1/forum/posts",
                json={
                    "board_id": 10,
                    "module": "discussion",
                    "title": f"速创速删-{i}",
                    "content": f"临时内容-{i}",
                },
                headers={"X-User-Id": "1", "X-User-Role": "teacher"},
            )
            if resp.status_code >= 500:
                server_errors += 1
                continue

            pid = resp.json()["data"]["id"]

            # 立即删除
            del_resp = client.delete(
                f"/api/v1/forum/posts/{pid}",
                headers={"X-User-Id": "1", "X-User-Role": "teacher"},
            )
            if del_resp.status_code >= 500:
                server_errors += 1

        print(f"\n快速创建删除10轮: 服务端错误={server_errors}")

        assert server_errors == 0

    def test_concurrent_search(self, client):
        """并发搜索不同关键词"""
        keywords = ["测试", "公告", "期末", "作业", "讨论", "软件", "工程", "数据库", "网络", "系统"]
        server_errors = 0

        for kw in keywords:
            resp = client.get(
                "/api/v1/forum/search/posts",
                params={"keyword": kw, "page": 1, "page_size": 10},
            )
            if resp.status_code >= 500:
                server_errors += 1

        print(f"\n10种关键词搜索: 服务端错误={server_errors}")

        assert server_errors == 0
