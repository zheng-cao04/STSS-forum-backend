# 设计模式报告：工厂方法模式在论坛后端内容审核中的应用

3220102918 曹正

## 一、问题描述

在 STSS 论坛后端中，用户可以举报帖子，也可以举报回复。两类举报最终都要生成一条 `ForumModeration` 审核记录，供管理员查询和处理。

但是，帖子和回复的取数方式不同：帖子举报可以直接从 `ForumPost` 读取标题、正文、作者和课程板块；回复举报需要先读取 `ForumReply`，再通过所属帖子补全课程板块等信息。如果把这些判断全部写在举报接口中，接口会同时承担参数接收、对象查询、字段组装和数据库保存等职责，代码会变得臃肿。

因此，后端需要把“根据不同举报目标创建审核记录”的逻辑集中封装起来，让举报接口只负责接收请求和保存审核记录。

## 二、设计模式选择

本场景采用工厂方法模式（Factory Method）。

工厂方法模式将对象创建过程封装到统一入口中，调用方不直接关心具体对象如何构造。在本系统中，`create_moderation_report` 是调用方，`build_moderation_from_target` 是工厂方法。它根据 `target_type` 判断举报目标是帖子还是回复，并返回统一的 `ForumModeration` 对象。

采用该模式后，举报接口不需要分别处理帖子和回复的字段来源，只需要调用工厂方法即可。

## 三、角色设计

| 角色 | 后端对应对象 | 说明 |
|---|---|---|
| Product | `ForumModeration` | 最终创建出的审核记录 |
| Creator / Factory Method | `build_moderation_from_target` | 根据目标类型创建审核记录 |
| Concrete Source A | `ForumPost` | 帖子举报的数据来源 |
| Concrete Source B | `ForumReply` | 回复举报的数据来源 |
| Client | `create_moderation_report` | 接收举报请求并调用工厂方法 |
| Type Parameter | `ModerationTargetType` | 决定创建哪一种审核记录 |

## 四、UML 类图

```text
+--------------------------+       +------------------------------+
| create_moderation_report | ----> | build_moderation_from_target |
+--------------------------+       +---------------+--------------+
                                                   |
                                   +---------------+---------------+
                                   |                               |
                                   v                               v
                             +-----------+                   +-----------+
                             | ForumPost |                   | ForumReply|
                             +-----+-----+                   +-----+-----+
                                   |                               |
                                   +---------------+---------------+
                                                   v
                                           +-----------------+
                                           | ForumModeration |
                                           +-----------------+
```

## 五、设计说明

当用户提交举报时，后端处理流程如下：

1. `create_moderation_report` 接收 `target_type`、`target_id` 和 `reason`。
2. 接口调用 `build_moderation_from_target`，不直接组装审核对象。
3. 工厂方法根据 `target_type` 查询 `ForumPost` 或 `ForumReply`。
4. 工厂方法把不同来源的数据转换为统一的 `ForumModeration`。
5. 接口将审核记录写入数据库并返回统一响应。

核心伪代码如下：

```python
def build_moderation_from_target(session, target_type, target_id, reporter, reason):
    if target_type == ModerationTargetType.post:
        post = session.get(ForumPost, target_id)
        return ForumModeration(
            target_type=target_type, target_id=target_id,
            title=post.title, content=post.content,
            author_name=post.author_name,
            reporter_name=reporter, reason=reason,
        )

    reply = session.get(ForumReply, target_id)
    return ForumModeration(
        target_type=target_type, target_id=target_id,
        title="回复内容审核", content=reply.content,
        author_name=reply.author_name,
        reporter_name=reporter, reason=reason,
    )
```

## 六、优点

（1）降低接口复杂度。举报接口只负责请求处理和数据保存，具体字段组装交给工厂方法完成。

（2）提高扩展性。如果后续支持举报附件、公告或课程资料，只需要在工厂方法中增加新的目标类型分支。

（3）统一数据格式。不同举报对象最终都会转换成 `ForumModeration`，便于管理员统一查询和处理。

综上，工厂方法模式适合用于论坛后端内容审核记录创建场景。它将不同举报目标的创建细节封装起来，提高了审核模块的可维护性。
