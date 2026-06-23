# STSS 智能教学服务系统

# 论坛交流子系统 Backend 系统设计报告

版本：1.0

编制人：STSS 项目开发团队论坛交流小组

提交日期：2026 年 6 月 23 日

文档状态：正式版

---

## 目 录

- 第 1 章 引言
  - 1.1 项目背景
  - 1.2 建设目标
  - 1.3 术语表
  - 1.4 文档结构
- 第 2 章 需求分析
  - 2.1 功能性需求
  - 2.2 非功能性需求
- 第 3 章 总体架构设计
  - 3.1 技术栈选型
  - 3.2 核心分层架构
  - 3.3 统一网关接入设计
  - 3.4 活跃度与审核流水设计
- 第 4 章 详细设计
  - 4.1 数据库设计
  - 4.2 核心接口契约
  - 4.3 权限与身份设计
  - 4.4 附件访问设计
- 第 5 章 容错机制与高可用设计
  - 5.1 网关与本地联调双路径兼容
  - 5.2 数据一致性与软删除策略
  - 5.3 活跃度 Outbox 机制
- 第 6 章 测试验证与质量保障
  - 6.1 接口功能测试
  - 6.2 网关附件路径兼容测试
  - 6.3 静态检查与持续质量控制
- 第 7 章 总结与展望
  - 7.1 设计总结
  - 7.2 后续优化方向
- 附录 A 核心接口清单
- 附录 B 部署环境说明

---

## 第 1 章 引言

### 1.1 项目背景

智能教学服务系统（Smart Teaching Service System，STSS）面向高校教学管理场景，覆盖基础信息、排课、选课、在线测试、成绩管理与课程论坛等多个子系统。论坛交流子系统承担课程讨论、课程公告、学生提问、教师答疑、资料附件、内容审核和活跃度统计等业务职责，是师生在教学活动中进行异步协作的重要入口。

论坛后端需要与统一网关、基础信息服务、选课服务和成绩服务保持契约一致。当前实现采用 FastAPI 构建 REST API，通过统一前缀 `/api/v1/forum` 对外暴露能力；部署时由 STSS Gateway 统一转发、鉴权并注入用户身份头。

### 1.2 建设目标

本子系统的核心建设目标如下：

- 课程空间统一：以课程论坛板块为组织单元，将课程、教学班、公告、帖子和回复关联起来。
- 交流闭环完整：支持公告发布、帖子创建、回复讨论、附件上传、帖子搜索和详情查看。
- 管理审核可控：支持教师或管理员维护课程板块、管理公告，并支持对帖子和回复进行举报、审核、隐藏和删除。
- 统计可追踪：记录帖子浏览、回复数量、热度分数和用户活跃度，为成绩管理或教学分析提供数据基础。
- 网关接入一致：统一使用 `/api/v1/forum/*` 路径和 `forum_service:8005` 服务地址，兼容公共网关的身份注入方式。
- 本地开发可运行：保留 `localhost:5000` 本地调试入口，降低前后端联调和单服务测试成本。

### 1.3 术语表

| 术语 | 说明 |
|---|---|
| STSS | Smart Teaching Service System，智能教学服务系统 |
| Forum Backend | 论坛交流子系统后端服务 |
| Gateway | STSS 统一公共网关，负责路由、鉴权和身份头注入 |
| Board | 课程论坛板块，承载某课程或教学班下的公告与帖子 |
| Announcement | 课程公告，通常由教师或管理员发布 |
| Post | 论坛帖子，由师生围绕课程内容创建 |
| Reply | 帖子回复，支持父回复关联，用于树形讨论展示 |
| Attachment | 帖子附件，存储于后端上传目录并返回可访问 URL |
| Moderation | 内容审核记录，用于处理帖子或回复举报 |
| Activity Outbox | 活跃度数据待投递记录，用于后续向成绩或分析服务同步 |

### 1.4 文档结构

本文档第 2 章说明论坛后端的功能性与非功能性需求；第 3 章说明系统总体架构、技术栈和网关接入设计；第 4 章详述数据模型、接口契约、权限与附件设计；第 5 章说明容错机制、高可用与数据一致性策略；第 6 章给出测试验证与质量保障结论；第 7 章总结当前设计并提出后续演进方向。

---

## 第 2 章 需求分析

### 2.1 功能性需求

论坛交流子系统需要覆盖课程教学交流的核心业务场景，按功能域划分如下。

#### 2.1.1 课程论坛板块管理

系统须支持课程论坛板块的创建、查询、更新和停用。板块信息包括课程编号、课程名称、教学班编号、板块标题、描述、状态和公告弹窗开关。教师和管理员可以维护板块，学生主要消费板块下的公告、帖子与讨论内容。

#### 2.1.2 公告管理

系统须支持教师或管理员在指定课程板块发布公告，公告具备置顶、弹窗、隐藏和删除等状态。公告列表需要支持按课程、教学班、板块、作者、状态和时间区间筛选，并按置顶与发布时间排序。

#### 2.1.3 帖子、回复与附件

系统须支持学生或教师创建课程帖子，帖子按 discussion、homework、exam、general 等模块分类。帖子支持查询、搜索、详情查看、更新和删除；回复支持楼层序号、父回复关联和树形返回；附件支持上传、列表查询、删除和静态访问。

帖子详情访问时应记录浏览日志并更新热度分数；回复创建和删除时应维护帖子回复数和热度分数，便于热门内容排序。

#### 2.1.4 搜索、统计与活跃度

系统须支持关键词检索帖子标题和内容，并支持按课程、教学班、作者和时间区间过滤。统计接口需要提供热门帖子列表和用户活跃度数据。活跃度计算综合发帖数、回复数、浏览数和点赞数，作为教学参与度分析的输入。

#### 2.1.5 内容审核

系统须支持对帖子和回复发起审核举报，生成审核记录。管理员可以处理审核记录，并将目标内容标记为 approved、hidden 或 deleted。审核结果应同步影响帖子或回复的可见状态。

### 2.2 非功能性需求

#### 2.2.1 性能需求

论坛接口以课程维度和分页查询为主要访问模式，应避免一次性向前端返回大量无界数据。列表接口统一提供 `page`、`page_size` 和 `pagination` 返回结构，并限制单页最大数量。热门帖子和活跃度统计在当前实现中基于数据库记录计算，后续可按课程和周期引入缓存或异步预计算。

#### 2.2.2 可用性与容错需求

系统须在统一网关和本地单服务两种运行方式下可用。生产路径使用 `/api/v1/forum/*`，本地 Docker 仍映射宿主机 `5000` 端口方便调试。附件访问同时支持新网关路径 `/api/v1/forum/uploads/*` 和旧本地路径 `/uploads/*`，保证历史数据和现有联调方式平滑过渡。

#### 2.2.3 安全需求

系统须依赖网关注入的 `X-User-Id`、`X-User-Role`、`X-User-Name` 识别当前用户。教师或管理员才能创建和维护板块、发布公告；普通用户只能修改或删除自己的帖子、回复和附件；管理员可以处理审核记录。接口统一返回结构化错误码，禁止将内部异常直接暴露给前端。

#### 2.2.4 可维护性需求

系统须保持清晰的模块边界：配置集中在 `app/config.py`，数据库模型集中在 `app/models.py`，请求数据结构集中在 `app/schemas.py`，路由逻辑集中在 `app/routers/forum.py`，跨服务调用客户端放在 `app/integrations`。通过 Pytest 和 Ruff 保障基本回归质量。

---

## 第 3 章 总体架构设计

### 3.1 技术栈选型

| 层次 | 技术 | 选型说明 |
|---|---|---|
| Web 框架 | FastAPI | 提供类型驱动的 REST API、依赖注入和 OpenAPI 能力 |
| 数据访问 | SQLModel / SQLAlchemy | 用统一模型表达数据库表结构和对象关系 |
| 配置管理 | pydantic-settings | 统一从环境变量和 `.env` 读取运行期配置 |
| 数据库 | SQLite 默认，本地可切换 PostgreSQL | SQLite 适合课程项目本地开发，生产可通过 `DATABASE_URL` 替换 |
| HTTP 客户端 | httpx | 用于后续调用基础信息、选课、成绩等内部服务 |
| 文件服务 | FastAPI StaticFiles | 挂载附件目录并提供静态访问能力 |
| 容器化 | Docker / Docker Compose | 统一构建、端口映射、健康检查和数据卷管理 |
| 质量保障 | Pytest / Ruff | 接口回归测试和静态规范检查 |

### 3.2 核心分层架构

系统采用前后端分离与网关转发架构，核心分层如下：

```text
浏览器 / 前端页面
        │
        │ /api/v1/forum/*
        ▼
STSS Gateway
  - 鉴权
  - 路由
  - 注入 X-User-* 身份头
        │
        │ http://forum_service:8005
        ▼
Forum Backend
  - FastAPI Router
  - 权限校验
  - 业务编排
  - 统一响应
        │
        ├── SQLModel 数据库表
        ├── StaticFiles 附件目录
        └── Integrations 跨服务客户端
```

论坛后端内部采用以下逻辑分层：

- API 层：`app/routers/forum.py`，负责路由、参数校验、分页、状态流转和响应组装。
- Schema 层：`app/schemas.py`，负责输入数据结构和字段约束。
- Model 层：`app/models.py`，负责数据库实体定义。
- Dependency 层：`app/deps.py`，负责当前用户解析和角色归一化。
- Integration 层：`app/integrations`，预留基础信息、选课、成绩服务调用客户端。
- Config 层：`app/config.py`，负责运行环境、服务地址和附件路径等配置。

### 3.3 统一网关接入设计

论坛后端对外暴露统一前缀：

```text
/api/v1/forum
```

部署侧推荐网关上游配置：

```text
FORUM_SERVICE_URL=forum_service:8005
```

Docker 镜像默认监听容器内 `8005` 端口，本地 Compose 将宿主机 `5000` 映射到容器内 `8005`，因此本地调试仍可访问：

```text
http://localhost:5000/api/v1/forum/healthz
```

生产环境下，请求路径由公共网关转发到论坛后端。网关负责用户 Token 校验，论坛后端只信任网关注入的用户身份头：

```text
X-User-Id
X-User-Role
X-User-Name
```

为了兼容本地开发和测试环境，后端也支持从 `Authorization: Bearer token-student` 等开发 Token 中解析用户身份，但该能力仅用于本地联调和自动化测试。

### 3.4 活跃度与审核流水设计

论坛后端包含两条辅助业务流水。

第一条是活跃度流水。系统记录浏览日志 `ForumViewLog`，并基于发帖数、回复数、浏览数和点赞数计算活跃度分数。对外提供 `/stats/user_activity` 和 `/internal/forum/activity` 两类接口，分别服务前端统计展示和跨服务数据读取。

第二条是内容审核流水。系统通过 `ForumModeration` 保存举报目标、举报原因、处理状态、处理人和处理时间。管理员处理审核记录后，系统同步更新被举报的帖子或回复状态，实现审核记录与内容可见性的联动。

---

## 第 4 章 详细设计

### 4.1 数据库设计

论坛后端当前包含以下核心实体。

#### 4.1.1 课程论坛板块实体（ForumBoard）

`ForumBoard` 表示课程或教学班对应的论坛空间。核心字段包括：

| 字段 | 含义 |
|---|---|
| id | 主键 |
| course_id | 课程编号 |
| course_name | 课程名称 |
| offering_id | 教学班或开课编号 |
| name | 板块标题 |
| description | 板块描述 |
| status | 板块状态，例如 active、inactive |
| popup_enabled | 是否启用公告弹窗 |
| created_at / updated_at | 创建与更新时间 |

#### 4.1.2 公告实体（Announcement）

`Announcement` 表示课程公告。公告绑定板块、课程和教学班，并包含置顶、弹窗和状态控制。

公告状态包括：

- `published`：已发布
- `hidden`：隐藏
- `deleted`：已删除

#### 4.1.3 帖子实体（ForumPost）

`ForumPost` 表示课程讨论帖子。核心字段包括板块、课程、模块、标题、内容、状态、置顶标记、浏览数、回复数、点赞数、热度分数和作者信息。

帖子模块包括：

- `discussion`：课程讨论
- `homework`：作业交流
- `exam`：考试交流
- `general`：通用交流

帖子状态包括：

- `published`：普通发布
- `hot`：热门
- `pinned`：置顶
- `hidden`：隐藏
- `deleted`：删除

#### 4.1.4 回复实体（ForumReply）

`ForumReply` 表示帖子回复。核心字段包括帖子编号、楼层号、父回复编号、内容、作者信息、点赞数、状态和创建时间。通过 `parent_reply_id` 支持树形回复展示。

#### 4.1.5 附件实体（ForumAttachment）

`ForumAttachment` 表示帖子附件。核心字段包括帖子编号、原始文件名、访问 URL、文件大小、MIME 类型、上传人和创建时间。文件实体存储于服务端上传目录，数据库只保存元信息和访问路径。

#### 4.1.6 浏览日志实体（ForumViewLog）

`ForumViewLog` 用于记录帖子详情访问行为，字段包括帖子编号、用户编号、课程编号和访问时间。该表为用户活跃度统计提供基础数据。

#### 4.1.7 活跃度 Outbox 实体（ActivityBatchOutbox）

`ActivityBatchOutbox` 保存待同步的论坛活跃度批次，包括课程编号、统计周期、JSON 载荷、状态和创建时间。该设计为后续向成绩管理或教学分析服务异步推送数据预留空间。

#### 4.1.8 审核实体（ForumModeration）

`ForumModeration` 表示内容审核记录。核心字段包括目标类型、目标编号、标题、内容、课程名称、作者、举报人、原因、状态、处理时间和处理人。

审核状态包括：

- `pending`：待处理
- `approved`：审核通过
- `hidden`：隐藏
- `deleted`：删除

### 4.2 核心接口契约

系统统一响应格式如下：

```json
{
  "code": 0,
  "message": "OK",
  "data": {}
}
```

异常响应保持相同外壳，`code` 使用业务错误码，`message` 表示错误类型，`data` 可为空或包含校验错误信息。

#### 4.2.1 课程板块接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/forum/boards` | 查询课程板块列表 |
| POST | `/api/v1/forum/boards` | 创建课程板块 |
| PUT | `/api/v1/forum/boards/{board_id}` | 更新课程板块 |
| DELETE | `/api/v1/forum/boards/{board_id}` | 停用课程板块 |

创建和更新板块需要教师或管理员权限，删除采用停用策略，将状态改为 inactive。

#### 4.2.2 公告接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/forum/announcements` | 查询公告列表 |
| POST | `/api/v1/forum/announcements` | 创建公告 |
| PUT | `/api/v1/forum/announcements/{announcement_id}` | 更新公告 |
| DELETE | `/api/v1/forum/announcements/{announcement_id}` | 软删除公告 |
| PUT | `/api/v1/forum/announcements/{announcement_id}/popup_toggle` | 切换公告弹窗状态 |

公告创建和弹窗切换需要教师或管理员权限。公告更新和删除要求作者本人或管理员操作。

#### 4.2.3 帖子与回复接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/forum/posts` | 查询帖子列表 |
| POST | `/api/v1/forum/posts` | 创建帖子 |
| GET | `/api/v1/forum/posts/{post_id}` | 查询帖子详情并记录浏览 |
| PUT | `/api/v1/forum/posts/{post_id}` | 更新帖子 |
| DELETE | `/api/v1/forum/posts/{post_id}` | 软删除帖子和关联回复 |
| GET | `/api/v1/forum/posts/{post_id}/replies` | 查询帖子回复 |
| POST | `/api/v1/forum/posts/{post_id}/replies` | 创建回复 |
| DELETE | `/api/v1/forum/replies/{reply_id}` | 软删除回复 |

帖子详情接口会增加浏览次数并写入浏览日志。创建回复时会增加帖子回复数并更新热度分数；当热度分数达到阈值时，普通帖子可自动转为热门状态。

#### 4.2.4 附件接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/forum/posts/{post_id}/attachments` | 上传帖子附件 |
| GET | `/api/v1/forum/posts/{post_id}/attachments` | 查询帖子附件列表 |
| DELETE | `/api/v1/forum/attachments/{attachment_id}` | 删除附件记录和本地文件 |
| GET | `/api/v1/forum/uploads/{file}` | 访问新上传附件 |
| GET | `/uploads/{file}` | 旧路径兼容访问 |

新上传附件统一返回 `/api/v1/forum/uploads/<file>`，以适配公共网关路径。旧 `/uploads/<file>` 仍保留，服务历史数据和本地联调。

#### 4.2.5 搜索、统计与活跃度接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/forum/search/posts` | 关键词检索帖子 |
| GET | `/api/v1/forum/stats/hot_posts` | 查询热门帖子 |
| GET | `/api/v1/forum/stats/user_activity` | 查询用户活跃度 |
| GET | `/api/v1/forum/internal/forum/activity` | 内部读取活跃度 |
| POST | `/api/v1/forum/forum/activity-batch` | 写入活跃度 Outbox |

活跃度分数当前按以下维度计算：

```text
activity_score = post_count * 5 + reply_count * 2 + view_count * 0.5 + like_count
```

#### 4.2.6 审核接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/forum/moderation` | 查询审核列表 |
| POST | `/api/v1/forum/moderation/reports` | 创建举报记录 |
| PUT | `/api/v1/forum/moderation/{moderation_id}/handle` | 处理审核记录 |

管理员处理审核时，若状态为 hidden 或 deleted，系统会同步修改目标帖子或回复的状态；若状态为 approved，系统可将隐藏内容恢复为 published。

#### 4.2.7 错误码规范

| 错误码 | 含义 |
|---|---|
| 50001 | 参数错误或目标资源不存在 |
| 50002 | 未授权操作 |
| 50101 | 帖子或公告不存在 |
| 50201 | 课程板块不存在 |
| 50202 | 当前用户不是教师或管理员 |
| 50301 | 回复不存在 |
| 50401 | 搜索关键词缺失 |

### 4.3 权限与身份设计

论坛后端通过 `get_current_user` 解析当前用户。生产环境由网关注入身份头，本地开发和测试可使用 Bearer mock token。

角色归一化规则如下：

- `student`：学生，默认具备发帖、回复、上传附件、删除本人内容等权限。
- `teacher`：教师，具备学生能力，并可维护板块、发布公告、切换公告弹窗。
- `admin`：管理员，具备全部管理能力，并可处理审核记录、删除任意违规内容。

核心权限函数包括：

- `ensure_teacher_or_admin`：限制教师或管理员操作。
- `ensure_author_or_admin`：限制作者本人或管理员操作。

该设计将身份解析与业务权限判断分离，便于后续替换真实统一身份服务。

### 4.4 附件访问设计

附件上传流程如下：

1. 前端调用 `POST /api/v1/forum/posts/{post_id}/attachments` 上传文件。
2. 后端校验帖子存在且未删除。
3. 后端用 UUID 前缀生成存储文件名，避免同名覆盖。
4. 文件写入 `UPLOAD_DIR` 目录。
5. 数据库写入附件元信息。
6. 响应返回 `/api/v1/forum/uploads/<stored_name>`。

附件删除流程如下：

1. 前端调用 `DELETE /api/v1/forum/attachments/{attachment_id}`。
2. 后端校验附件存在，以及当前用户为上传者或管理员。
3. 后端根据新旧路径前缀解析本地文件名。
4. 删除本地文件和数据库记录。

该设计同时解决公共网关路径统一和历史 `/uploads` 兼容问题。

---

## 第 5 章 容错机制与高可用设计

### 5.1 网关与本地联调双路径兼容

论坛后端采用双路径兼容策略：

- 生产网关路径：`/api/v1/forum/*`
- 本地宿主机入口：`http://localhost:5000/api/v1/forum/*`
- 容器内服务地址：`forum_service:8005`

该策略使服务既能被统一网关标准化接入，也能在后端小组本地独立启动和测试。

### 5.2 数据一致性与软删除策略

系统对帖子、回复、公告等核心内容采用软删除策略，避免误删导致业务审计信息丢失。

- 删除帖子时，将帖子状态改为 `deleted`，并同步将关联回复状态改为 `deleted`。
- 删除回复时，将回复状态改为 `deleted`，并回退帖子回复计数和热度分数。
- 删除公告时，将公告状态改为 `deleted`，列表默认过滤 deleted 数据。
- 停用板块时，将板块状态改为 `inactive`，保留历史关联数据。

软删除策略保障了数据可追溯性，也为后续内容恢复和审计留出空间。

### 5.3 活跃度 Outbox 机制

当前系统已具备 `ActivityBatchOutbox` 表，用于保存待同步的活跃度批次。前端或内部服务可调用 `/forum/activity-batch` 写入统计载荷，后续可由后台任务读取 outbox 并投递到成绩管理或教学分析服务。

Outbox 机制的优点如下：

- 降低跨服务同步对主业务接口的影响。
- 支持失败重试和状态追踪。
- 保留统计数据投递记录，便于排查与审计。

当前实现已完成 outbox 写入，后续可补充后台投递 Worker 和重试状态流转。

---

## 第 6 章 测试验证与质量保障

### 6.1 接口功能测试

论坛后端已通过 Pytest 覆盖核心业务流程：

- 发帖、回复、搜索和统计接口联动。
- 当前用户解析与“我的帖子”查询。
- 公告创建、弹窗切换、更新和查询。
- 板块创建、更新、停用和审核处理。

测试命令：

```bash
uv run pytest
```

当前测试结果为 5 个用例全部通过。

### 6.2 网关附件路径兼容测试

新增测试覆盖附件网关路径兼容：

- 上传附件后返回路径必须以 `/api/v1/forum/uploads/` 开头。
- 新路径可直接读取附件内容。
- 旧路径 `/uploads/` 仍可读取同一文件。
- 附件列表返回的新路径保持一致。
- 上传者可删除本人附件。

该测试验证了论坛后端在不修改前端业务代码的前提下，具备统一网关附件路径兼容能力。

### 6.3 静态检查与持续质量控制

系统使用 Ruff 执行静态检查，控制导入、命名、语法和基础风格问题。

测试命令：

```bash
uv run ruff check .
```

当前静态检查结果为全部通过。

---

## 第 7 章 总结与展望

### 7.1 设计总结

论坛交流子系统后端围绕课程教学讨论场景，完成了课程板块、公告、帖子、回复、附件、搜索、统计、活跃度和内容审核等核心能力。系统采用 FastAPI 与 SQLModel 实现清晰的 REST API 与数据模型，通过统一响应结构和错误码降低前后端联调成本。

在部署层面，系统已对齐公共网关默认约定：容器内监听 `8005`，服务地址为 `forum_service:8005`，对外路径为 `/api/v1/forum/*`。附件访问也已统一到 `/api/v1/forum/uploads/*`，并保留旧 `/uploads/*` 兼容能力。

在质量保障层面，系统已具备接口回归测试和静态检查，能够覆盖当前核心业务链路。

### 7.2 后续优化方向

后续可从以下方向继续完善：

- 引入数据库迁移工具，统一管理 SQLite/PostgreSQL 表结构演进。
- 将热门帖子和活跃度统计改为增量计算或定时预聚合，提升大数据量下的查询性能。
- 完善 Outbox 后台投递 Worker，实现向成绩管理服务的可靠同步。
- 接入真实基础信息和选课服务，校验课程板块成员、教师授课关系和学生选课关系。
- 增加附件大小、类型白名单和病毒扫描策略。
- 增加审计日志，记录管理员审核和删除操作。
- 在部署仓库中将 placeholder `forum_service` 替换为真实论坛后端镜像。

---

## 附录 A 核心接口清单

统一前缀：

```text
/api/v1/forum
```

接口清单：

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/healthz` | 健康检查 |
| GET | `/me` | 当前用户信息 |
| GET | `/boards` | 板块列表 |
| POST | `/boards` | 创建板块 |
| PUT | `/boards/{board_id}` | 更新板块 |
| DELETE | `/boards/{board_id}` | 停用板块 |
| GET | `/announcements` | 公告列表 |
| POST | `/announcements` | 创建公告 |
| PUT | `/announcements/{announcement_id}` | 更新公告 |
| DELETE | `/announcements/{announcement_id}` | 删除公告 |
| PUT | `/announcements/{announcement_id}/popup_toggle` | 切换公告弹窗 |
| GET | `/posts` | 帖子列表 |
| POST | `/posts` | 创建帖子 |
| GET | `/posts/{post_id}` | 帖子详情 |
| PUT | `/posts/{post_id}` | 更新帖子 |
| DELETE | `/posts/{post_id}` | 删除帖子 |
| POST | `/posts/{post_id}/attachments` | 上传附件 |
| GET | `/posts/{post_id}/attachments` | 附件列表 |
| DELETE | `/attachments/{attachment_id}` | 删除附件 |
| GET | `/posts/{post_id}/replies` | 回复列表 |
| POST | `/posts/{post_id}/replies` | 创建回复 |
| DELETE | `/replies/{reply_id}` | 删除回复 |
| GET | `/search/posts` | 搜索帖子 |
| GET | `/stats/hot_posts` | 热门帖子 |
| GET | `/stats/user_activity` | 用户活跃度 |
| GET | `/internal/forum/activity` | 内部活跃度读取 |
| POST | `/forum/activity-batch` | 写入活跃度 Outbox |
| GET | `/moderation` | 审核列表 |
| POST | `/moderation/reports` | 创建举报 |
| PUT | `/moderation/{moderation_id}/handle` | 处理审核 |

---

## 附录 B 部署环境说明

### B.1 Docker 运行参数

论坛后端 Docker 镜像默认监听：

```text
8005
```

本地 Compose 映射：

```text
localhost:5000 -> container:8005
```

### B.2 关键环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| APP_NAME | STSS Forum Backend | 应用名称 |
| ENV | development | 运行环境 |
| FORUM_PORT | 8005 | 容器内监听端口 |
| DATABASE_URL | sqlite:///./data/forum.db | 数据库连接 |
| UPLOAD_DIR | uploads | 附件目录 |
| PUBLIC_UPLOAD_PREFIX | /api/v1/forum/uploads | 新附件访问前缀 |
| LEGACY_UPLOAD_PREFIX | /uploads | 旧附件访问前缀 |
| FRONTEND_ORIGINS | localhost 前端地址 | 本地 CORS 配置 |
| SKIP_EXTERNAL_CHECKS | true | 是否跳过外部服务校验 |
| INFO_SERVICE_URL | http://localhost:8002 | 基础信息服务地址 |
| COURSE_SELECTION_SERVICE_URL | http://localhost:8003 | 选课服务地址 |
| SCORE_SERVICE_URL | http://localhost:8004 | 成绩服务地址 |
| INTERNAL_TOKEN | dev-internal-token | 内部调用 Token |

### B.3 网关接入参数

部署仓库接入论坛后端时，应将网关上游设置为：

```text
FORUM_SERVICE_URL=forum_service:8005
```

网关路由：

```text
/api/v1/forum/*
```

健康检查：

```text
GET /api/v1/forum/healthz
```

