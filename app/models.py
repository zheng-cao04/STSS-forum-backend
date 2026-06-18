from datetime import UTC, datetime
from enum import StrEnum

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(UTC)


class NoticeStatus(StrEnum):
    published = "published"
    hidden = "hidden"
    deleted = "deleted"


class PostStatus(StrEnum):
    published = "published"
    hot = "hot"
    pinned = "pinned"
    hidden = "hidden"
    deleted = "deleted"


class PostModule(StrEnum):
    discussion = "discussion"
    homework = "homework"
    exam = "exam"
    general = "general"


class ReplyStatus(StrEnum):
    published = "published"
    hidden = "hidden"
    deleted = "deleted"


class ForumBoard(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    course_id: str = Field(index=True)
    course_name: str = ""
    offering_id: str | None = Field(default=None, index=True)
    name: str
    description: str = ""
    status: str = Field(default="active", index=True)
    popup_enabled: bool = False
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime | None = None


class Announcement(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    board_id: int = Field(index=True, foreign_key="forumboard.id")
    course_id: str = Field(index=True)
    offering_id: str | None = Field(default=None, index=True)
    title: str
    content: str
    pinned: bool = False
    popup: bool = False
    status: NoticeStatus = Field(default=NoticeStatus.published, index=True)
    author_id: int = Field(index=True)
    created_at: datetime = Field(default_factory=utcnow, index=True)
    updated_at: datetime | None = None


class ForumPost(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    board_id: int = Field(index=True, foreign_key="forumboard.id")
    course_id: str = Field(index=True)
    offering_id: str | None = Field(default=None, index=True)
    module: PostModule = Field(index=True)
    title: str
    content: str
    status: PostStatus = Field(default=PostStatus.published, index=True)
    pinned: bool = False
    views_count: int = 0
    replies_count: int = 0
    likes_count: int = 0
    hot_score: float = 0
    author_id: int = Field(index=True)
    author_name: str = ""
    author_role: str = "student"
    created_at: datetime = Field(default_factory=utcnow, index=True)
    updated_at: datetime | None = None


class ForumReply(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    post_id: int = Field(index=True, foreign_key="forumpost.id")
    floor: int = Field(index=True)
    parent_reply_id: int | None = Field(default=None, index=True)
    content: str
    author_id: int = Field(index=True)
    author_name: str = ""
    author_role: str = "student"
    likes_count: int = 0
    status: ReplyStatus = Field(default=ReplyStatus.published, index=True)
    created_at: datetime = Field(default_factory=utcnow, index=True)
    updated_at: datetime | None = None


class ForumAttachment(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    post_id: int = Field(index=True, foreign_key="forumpost.id")
    file_name: str
    file_url: str
    file_size: int
    mime_type: str
    uploader_id: int = Field(index=True)
    created_at: datetime = Field(default_factory=utcnow)


class ForumViewLog(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    post_id: int = Field(index=True)
    user_id: int = Field(index=True)
    course_id: str = Field(index=True)
    created_at: datetime = Field(default_factory=utcnow, index=True)


class ActivityBatchOutbox(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    course_id: str = Field(index=True)
    period_start: str
    period_end: str
    payload_json: str
    status: str = Field(default="pending", index=True)
    created_at: datetime = Field(default_factory=utcnow)


class ModerationStatus(StrEnum):
    pending = "pending"
    approved = "approved"
    hidden = "hidden"
    deleted = "deleted"


class ModerationTargetType(StrEnum):
    post = "post"
    reply = "reply"


class ForumModeration(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    target_type: ModerationTargetType = Field(index=True)
    target_id: int = Field(index=True)
    title: str
    content: str
    course_name: str = ""
    author_name: str = ""
    reporter_name: str = ""
    reason: str
    status: ModerationStatus = Field(default=ModerationStatus.pending, index=True)
    created_at: datetime = Field(default_factory=utcnow, index=True)
    handled_at: datetime | None = None
    handler_name: str | None = None
