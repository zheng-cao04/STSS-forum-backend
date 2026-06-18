from sqlmodel import Session, select

from app.models import (
    Announcement,
    ForumBoard,
    ForumModeration,
    ForumPost,
    ForumReply,
    ModerationTargetType,
    PostModule,
    PostStatus,
)


def seed_forum_boards(session: Session) -> None:
    seed_boards = [
        ForumBoard(
            id=10,
            course_id="SE-2026",
            course_name="软件工程",
            offering_id="SE-2026-SPRING",
            name="软件工程课程论坛",
            description="用于发布课程公告、项目讨论、作业答疑和小组交流。",
            popup_enabled=True,
        ),
        ForumBoard(
            id=11,
            course_id="CS101",
            course_name="程序设计基础",
            offering_id="CS101-SPRING",
            name="程序设计基础课程论坛",
            description="用于课程通知、答疑讨论和资料共享。",
        ),
    ]
    for seed_board in seed_boards:
        existing = session.get(ForumBoard, seed_board.id)
        if existing:
            existing.course_name = seed_board.course_name
            existing.offering_id = seed_board.offering_id
            existing.popup_enabled = seed_board.popup_enabled
            session.add(existing)
        else:
            session.add(seed_board)
    session.commit()

    if not session.exec(select(ForumPost)).first():
        session.add_all(
            [
                Announcement(
                    board_id=10,
                    course_id="SE-2026",
                    offering_id="SE-2026-SPRING",
                    title="项目展示材料提交提醒",
                    content="请各小组在本周日前提交展示材料、需求分析和设计说明文档。",
                    pinned=True,
                    popup=True,
                    author_id=1,
                ),
                ForumPost(
                    board_id=10,
                    course_id="SE-2026",
                    offering_id="SE-2026-SPRING",
                    module=PostModule.discussion,
                    title="关于论坛交流子系统接口字段的疑问",
                    content="公告、帖子、回复和搜索模块的字段是否都按照现有 API 文档来设计？",
                    status=PostStatus.hot,
                    views_count=236,
                    replies_count=1,
                    likes_count=18,
                    hot_score=92.5,
                    author_id=7,
                    author_name="张同学",
                    author_role="student",
                ),
                ForumPost(
                    board_id=11,
                    course_id="CS101",
                    offering_id="CS101-SPRING",
                    module=PostModule.exam,
                    title="期末复习资料汇总",
                    content="这里整理课程重点、历年题型和常见编程错误，欢迎同学们在回复区补充。",
                    status=PostStatus.pinned,
                    pinned=True,
                    views_count=412,
                    replies_count=0,
                    likes_count=35,
                    hot_score=96.8,
                    author_id=2,
                    author_name="王老师",
                    author_role="teacher",
                ),
            ]
        )
        session.commit()
    first_post = session.exec(
        select(ForumPost).where(ForumPost.title == "关于论坛交流子系统接口字段的疑问")
    ).first()
    if first_post and first_post.id:
        session.add(
            ForumReply(
                post_id=first_post.id,
                floor=1,
                content="前端可以先按文档字段 mock，后续真实接口确定后再统一对齐。",
                author_id=8,
                author_name="助教",
                author_role="teacher",
                likes_count=6,
            )
        )
        session.commit()

    if not session.exec(select(ForumModeration)).first() and first_post and first_post.id:
        session.add(
            ForumModeration(
                target_type=ModerationTargetType.post,
                target_id=first_post.id,
                title=first_post.title,
                content=first_post.content,
                course_name="软件工程",
                author_name=first_post.author_name,
                reporter_name="李同学",
                reason="内容本身无违规，仅用于演示审核通过状态",
            )
        )
        session.commit()
