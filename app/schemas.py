from typing import Any

from pydantic import BaseModel, Field

from app.models import ModerationStatus, ModerationTargetType, NoticeStatus, PostModule, PostStatus


class Page(BaseModel):
    total: int
    page: int
    page_size: int


class AnnouncementCreate(BaseModel):
    board_id: int
    title: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1)
    pinned: bool = False
    popup: bool = False


class BoardCreate(BaseModel):
    course_id: str = Field(min_length=1, max_length=64)
    course_name: str = Field(min_length=1, max_length=120)
    offering_id: str | None = None
    title: str = Field(min_length=1, max_length=120)
    description: str = ""
    status: str = "active"
    popup_enabled: bool = False


class BoardUpdate(BaseModel):
    course_id: str | None = Field(default=None, min_length=1, max_length=64)
    course_name: str | None = Field(default=None, min_length=1, max_length=120)
    offering_id: str | None = None
    title: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    status: str | None = None
    popup_enabled: bool | None = None


class AnnouncementUpdate(BaseModel):
    board_id: int | None = None
    title: str | None = Field(default=None, min_length=1, max_length=120)
    content: str | None = Field(default=None, min_length=1)
    pinned: bool | None = None
    popup: bool | None = None
    status: NoticeStatus | None = None


class PostCreate(BaseModel):
    board_id: int
    course_id: str | None = None
    offering_id: str | None = None
    module: PostModule
    title: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1)
    pinned: bool = False


class PostUpdate(BaseModel):
    board_id: int | None = None
    title: str | None = Field(default=None, min_length=1, max_length=120)
    content: str | None = Field(default=None, min_length=1)
    module: PostModule | None = None
    pinned: bool | None = None
    status: PostStatus | None = None


class ReplyCreate(BaseModel):
    parent_reply_id: int | None = None
    content: str = Field(min_length=1)


class ActivityBatchItem(BaseModel):
    user_id: int
    post_count: int = 0
    reply_count: int = 0
    view_count: int = 0
    like_count: int = 0
    activity_score: float = 0


class ActivityBatchForm(BaseModel):
    period_start: str
    period_end: str
    course_id: str
    items: list[ActivityBatchItem]


class ModerationReportCreate(BaseModel):
    target_type: ModerationTargetType
    target_id: int
    reason: str = Field(min_length=1, max_length=300)
    reporter_name: str | None = None


class ModerationHandleForm(BaseModel):
    status: ModerationStatus
    reason: str | None = Field(default=None, max_length=300)


class ExternalCheckResult(BaseModel):
    allowed: bool
    reason: str | None = None
    raw: dict[str, Any] | None = None
