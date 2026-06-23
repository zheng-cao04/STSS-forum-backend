# STSS Forum Backend

D 组论坛交流子系统后端，面向 `SSTS-frontend` 中的 `src/api/modules/forum.ts`。

## 技术栈

- FastAPI
- SQLModel
- SQLite 默认本地开发；通过 `DATABASE_URL` 可切换 PostgreSQL
- 统一响应：`{"code": 0, "message": "success", "data": ...}`

## 快速启动

```bash
uv sync --group dev
cp .env.example .env
uv run uvicorn app.main:app --host 0.0.0.0 --port 5000
```

前端保持：

```ts
export const FORUM_API = "/api/v1/forum";
```

如前端 dev server 使用 Vite 代理，把 `/api` 代理到 `http://localhost:8000` 即可。
如只接本组论坛服务，把 `/api/v1/forum` 代理到 `http://localhost:5000` 即可。

## Docker 启动

```bash
docker compose up --build
```

服务端口：

```text
宿主机：http://localhost:5000
容器内：http://forum_service:8005
```

健康检查：

```text
http://localhost:5000/api/v1/health
```

统一网关接入时，论坛后端作为独立镜像由 `STSS-deploy` 编排，不需要把代码合并到部署仓库。上游服务地址使用：

```text
FORUM_SERVICE_URL=forum_service:8005
```

网关负责鉴权、CORS 和路径转发；论坛服务只读取网关注入的 `X-User-Id`、`X-User-Role`、`X-User-Name` 请求头。服务自身默认不设置 CORS 响应头；本地绕过网关直连调试时可设置 `ENABLE_CORS=true`。

附件新上传后默认返回 `/api/v1/forum/uploads/<file>`，后端仍保留旧 `/uploads/<file>` 静态挂载用于本地和历史数据兼容。

Compose 会创建两个 named volumes：

- `forum_data`：SQLite 数据库，默认 `/app/data/forum.db`
- `forum_uploads`：附件上传目录，默认 `/app/uploads`

停止并保留数据：

```bash
docker compose down
```

停止并清空本服务 Docker 数据：

```bash
docker compose down -v
```

## 已覆盖接口

- `GET /api/v1/forum/announcements`
- `POST /api/v1/forum/announcements`
- `PUT /api/v1/forum/announcements/{announcement_id}`
- `DELETE /api/v1/forum/announcements/{announcement_id}`
- `PUT /api/v1/forum/announcements/{announcement_id}/popup_toggle`
- `GET /api/v1/forum/posts`
- `POST /api/v1/forum/posts`
- `GET /api/v1/forum/posts/{post_id}`
- `PUT /api/v1/forum/posts/{post_id}`
- `DELETE /api/v1/forum/posts/{post_id}`
- `POST /api/v1/forum/posts/{post_id}/attachments`
- `DELETE /api/v1/forum/attachments/{attachment_id}`
- `GET /api/v1/forum/posts/{post_id}/replies`
- `POST /api/v1/forum/posts/{post_id}/replies`
- `DELETE /api/v1/forum/replies/{reply_id}`
- `GET /api/v1/forum/search/posts`
- `GET /api/v1/forum/stats/hot_posts`
- `GET /api/v1/forum/stats/user_activity`
- `GET /api/v1/forum/internal/forum/activity`
- `POST /api/v1/forum/forum/activity-batch`
- `GET /api/v1/health`
- `GET /api/v1/forum/healthz`
- `GET /api/v1/forum/boards`
- `POST /api/v1/forum/boards`
- `PUT /api/v1/forum/boards/{board_id}`
- `DELETE /api/v1/forum/boards/{board_id}`（软停用）
- `GET /api/v1/forum/posts/{post_id}/attachments`
- `GET /api/v1/forum/moderation`
- `POST /api/v1/forum/moderation/reports`
- `PUT /api/v1/forum/moderation/{moderation_id}/handle`

## 本地身份

网关接入前，服务会从请求头读取：

- `X-User-Id`
- `X-User-Role`
- `X-User-Name`

没有这些头时使用开发默认用户：`id=1, role=teacher`。
