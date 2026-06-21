import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlmodel import Session, select

from app.config import Settings, get_settings
from app.database import get_session
from app.deps import CurrentUser, get_current_user
from app.models import (
    ActivityBatchOutbox,
    Announcement,
    ForumAttachment,
    ForumBoard,
    ForumModeration,
    ForumPost,
    ForumReply,
    ForumViewLog,
    ModerationStatus,
    ModerationTargetType,
    NoticeStatus,
    PostModule,
    PostStatus,
    ReplyStatus,
)
from app.response import fail, ok
from app.schemas import (
    ActivityBatchForm,
    AnnouncementCreate,
    AnnouncementUpdate,
    BoardCreate,
    BoardUpdate,
    ModerationHandleForm,
    ModerationReportCreate,
    PostCreate,
    PostUpdate,
    ReplyCreate,
)

router = APIRouter(prefix="/api/v1/forum", tags=["forum"])


def now() -> datetime:
    return datetime.now(UTC)


def page_slice(items: list, page: int, page_size: int) -> tuple[list, dict]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    start = (page - 1) * page_size
    return items[start : start + page_size], {
        "total": len(items),
        "page": page,
        "page_size": page_size,
    }


def dt(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    return comparable_dt(parsed)


def comparable_dt(value: datetime | None) -> datetime:
    if value is None:
        return datetime.min
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def resolve_author_id(value: str | None, user: CurrentUser) -> int | None:
    if value in {None, ""}:
        return None
    if value == "me":
        return user.id
    try:
        return int(value)
    except ValueError as exc:
        raise fail(400, 50001, "INVALID_PARAMS") from exc


def get_board_or_404(session: Session, board_id: int) -> ForumBoard:
    board = session.get(ForumBoard, board_id)
    if not board:
        raise fail(404, 50201, "BOARD_NOT_FOUND")
    return board


def ensure_author_or_admin(record_author_id: int, user: CurrentUser) -> None:
    if user.is_admin or user.id == record_author_id:
        return
    raise fail(403, 50002, "UNAUTHORIZED")


def ensure_teacher_or_admin(user: CurrentUser) -> None:
    if not user.is_teacher_or_admin:
        raise fail(403, 50202, "FORBIDDEN_NOT_TEACHER")


def announcement_out(item: Announcement) -> dict:
    return {
        "id": item.id,
        "board_id": item.board_id,
        "course_id": item.course_id,
        "title": item.title,
        "content": item.content,
        "pinned": item.pinned,
        "popup": item.popup,
        "status": item.status,
        "author_id": item.author_id,
        "created_at": dt(item.created_at),
        "updated_at": dt(item.updated_at),
    }


def board_out(item: ForumBoard) -> dict:
    created_at = dt(item.created_at)
    updated_at = dt(item.updated_at) or created_at
    return {
        "id": item.id,
        "course_id": item.course_id,
        "course_name": item.course_name,
        "offering_id": item.offering_id,
        "title": item.name,
        "name": item.name,
        "description": item.description,
        "status": item.status,
        "popup_enabled": item.popup_enabled,
        "created_at": created_at,
        "updated_at": updated_at,
        # Compatibility aliases for the existing mock view naming style.
        "courseId": item.course_id,
        "courseName": item.course_name,
        "offeringId": item.offering_id,
        "popupEnabled": item.popup_enabled,
        "createdAt": created_at,
        "updatedAt": updated_at,
    }


def post_out(item: ForumPost, board: ForumBoard | None = None) -> dict:
    data = {
        "id": item.id,
        "board_id": item.board_id,
        "course_id": item.course_id,
        "module": item.module,
        "title": item.title,
        "content": item.content,
        "status": item.status,
        "pinned": item.pinned,
        "views_count": item.views_count,
        "replies_count": item.replies_count,
        "likes_count": item.likes_count,
        "hot_score": item.hot_score,
        "author_id": item.author_id,
        "created_at": dt(item.created_at),
        "updated_at": dt(item.updated_at),
    }
    if board:
        data.update(
            {
                "board_name": board.name,
                "author_name": item.author_name,
                "author_role": item.author_role,
            }
        )
    return data


def reply_out(item: ForumReply) -> dict:
    return {
        "id": item.id,
        "post_id": item.post_id,
        "floor": item.floor,
        "parent_reply_id": item.parent_reply_id,
        "content": item.content,
        "author_id": item.author_id,
        "likes_count": item.likes_count,
        "status": item.status,
        "created_at": dt(item.created_at),
    }


def attachment_out(item: ForumAttachment) -> dict:
    return {
        "id": item.id,
        "post_id": item.post_id,
        "file_name": item.file_name,
        "file_url": item.file_url,
        "file_size": item.file_size,
        "mime_type": item.mime_type,
        "uploader_id": item.uploader_id,
        "created_at": dt(item.created_at),
    }


def moderation_out(item: ForumModeration) -> dict:
    created_at = dt(item.created_at)
    handled_at = dt(item.handled_at)
    return {
        "id": item.id,
        "target_type": item.target_type,
        "target_id": item.target_id,
        "title": item.title,
        "content": item.content,
        "course_name": item.course_name,
        "author_name": item.author_name,
        "reporter_name": item.reporter_name,
        "reason": item.reason,
        "status": item.status,
        "created_at": created_at,
        "handled_at": handled_at,
        "handler_name": item.handler_name,
        # Compatibility aliases for the existing mock view naming style.
        "targetType": item.target_type,
        "targetId": item.target_id,
        "courseName": item.course_name,
        "authorName": item.author_name,
        "reporterName": item.reporter_name,
        "createdAt": created_at,
        "handledAt": handled_at,
        "handlerName": item.handler_name,
    }


def build_moderation_from_target(
    session: Session,
    target_type: ModerationTargetType,
    target_id: int,
    reporter_name: str,
    reason: str,
) -> ForumModeration:
    if target_type == ModerationTargetType.post:
        post = session.get(ForumPost, target_id)
        if not post or post.status == PostStatus.deleted:
            raise fail(404, 50101, "POST_NOT_FOUND")
        board = session.get(ForumBoard, post.board_id)
        return ForumModeration(
            target_type=target_type,
            target_id=target_id,
            title=post.title,
            content=post.content,
            course_name=board.course_name if board else post.course_id,
            author_name=post.author_name,
            reporter_name=reporter_name,
            reason=reason,
        )
    reply = session.get(ForumReply, target_id)
    if not reply or reply.status == ReplyStatus.deleted:
        raise fail(404, 50301, "REPLY_NOT_FOUND")
    post = session.get(ForumPost, reply.post_id)
    board = session.get(ForumBoard, post.board_id) if post else None
    return ForumModeration(
        target_type=target_type,
        target_id=target_id,
        title="回复内容审核",
        content=reply.content,
        course_name=board.course_name if board else "",
        author_name=reply.author_name,
        reporter_name=reporter_name,
        reason=reason,
    )


def activity_items(
    session: Session,
    course_id: str | None,
    offering_id: str | None,
    period: str,
) -> list[dict]:
    posts = session.exec(select(ForumPost).where(ForumPost.status != PostStatus.deleted)).all()
    replies = session.exec(select(ForumReply).where(ForumReply.status != ReplyStatus.deleted)).all()
    views = session.exec(select(ForumViewLog)).all()
    if course_id:
        posts = [item for item in posts if item.course_id == course_id]
        views = [item for item in views if item.course_id == course_id]
    if offering_id:
        posts = [item for item in posts if item.offering_id == offering_id]
    course_post_ids = {item.id for item in posts}
    replies = [item for item in replies if item.post_id in course_post_ids]

    users = sorted(
        {item.author_id for item in posts}
        | {item.author_id for item in replies}
        | {item.user_id for item in views}
    )
    start, end = period_bounds(period)
    result = []
    for user_id in users:
        user_posts = [item for item in posts if item.author_id == user_id]
        user_replies = [item for item in replies if item.author_id == user_id]
        user_views = [item for item in views if item.user_id == user_id]
        like_count = sum(item.likes_count for item in user_posts) + sum(
            item.likes_count for item in user_replies
        )
        result.append(
            {
                "user_id": user_id,
                "course_id": course_id or (user_posts[0].course_id if user_posts else ""),
                "period_start": start,
                "period_end": end,
                "post_count": len(user_posts),
                "reply_count": len(user_replies),
                "view_count": len(user_views),
                "like_count": like_count,
                "activity_score": (
                    len(user_posts) * 5
                    + len(user_replies) * 2
                    + len(user_views) * 0.5
                    + like_count
                ),
            }
        )
    return result


def period_bounds(period: str) -> tuple[str, str]:
    today = datetime.now(UTC).date()
    if period == "week":
        start = today.fromordinal(today.toordinal() - today.weekday())
    elif period == "month":
        start = today.replace(day=1)
    else:
        start = today
    return start.isoformat(), today.isoformat()


@router.get("/healthz")
def healthz() -> dict:
    return ok({"status": "ok", "service": "forum"})


@router.get("/me")
def get_me(user: CurrentUser = Depends(get_current_user)) -> dict:
    frontend_role = "academic_admin" if user.role == "admin" else user.role
    return ok(
        {
            "id": user.id,
            "name": user.name,
            "frontend_role": frontend_role,
            "backend_role": user.role,
        }
    )


@router.get("/boards")
def list_boards(
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    course_id: str | None = None,
    status: str | None = None,
    session: Session = Depends(get_session),
) -> dict:
    boards = session.exec(select(ForumBoard).order_by(ForumBoard.id)).all()
    if keyword:
        lowered = keyword.lower()
        boards = [
            board
            for board in boards
            if lowered in board.course_id.lower()
            or lowered in board.course_name.lower()
            or lowered in board.name.lower()
            or lowered in board.description.lower()
        ]
    if course_id:
        boards = [board for board in boards if board.course_id == course_id]
    if status:
        boards = [board for board in boards if board.status == status]
    paged, pagination = page_slice(boards, page, page_size)
    return ok({"items": [board_out(board) for board in paged], "pagination": pagination})


@router.post("/boards")
def create_board(
    payload: BoardCreate,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    ensure_teacher_or_admin(user)
    item = ForumBoard(
        course_id=payload.course_id,
        course_name=payload.course_name,
        offering_id=payload.offering_id,
        name=payload.title,
        description=payload.description,
        status=payload.status,
        popup_enabled=payload.popup_enabled,
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return ok(board_out(item))


@router.put("/boards/{board_id}")
def update_board(
    board_id: int,
    payload: BoardUpdate,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    ensure_teacher_or_admin(user)
    item = get_board_or_404(session, board_id)
    field_map = {
        "course_id": "course_id",
        "course_name": "course_name",
        "offering_id": "offering_id",
        "title": "name",
        "description": "description",
        "status": "status",
        "popup_enabled": "popup_enabled",
    }
    for payload_field, model_field in field_map.items():
        value = getattr(payload, payload_field)
        if value is not None:
            setattr(item, model_field, value)
    item.updated_at = now()
    session.add(item)
    session.commit()
    session.refresh(item)
    return ok(board_out(item))


@router.delete("/boards/{board_id}")
def delete_board(
    board_id: int,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    ensure_teacher_or_admin(user)
    item = get_board_or_404(session, board_id)
    item.status = "inactive"
    item.updated_at = now()
    session.add(item)
    session.commit()
    return ok(None)


@router.get("/announcements")
def get_announcement_list(
    page: int = 1,
    page_size: int = 10,
    course_id: str | None = None,
    offering_id: str | None = None,
    board_id: int | None = None,
    author_id: int | None = None,
    status: NoticeStatus | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    session: Session = Depends(get_session),
) -> dict:
    _ = sort_by
    items = session.exec(select(Announcement)).all()
    if course_id:
        items = [item for item in items if item.course_id == course_id]
    if offering_id:
        items = [item for item in items if item.offering_id == offering_id]
    if board_id:
        items = [item for item in items if item.board_id == board_id]
    if author_id:
        items = [item for item in items if item.author_id == author_id]
    if status:
        items = [item for item in items if item.status == status]
    else:
        items = [item for item in items if item.status != NoticeStatus.deleted]
    start_dt = parse_date(start_date)
    end_dt = parse_date(end_date)
    if start_dt:
        items = [item for item in items if comparable_dt(item.created_at) >= start_dt]
    if end_dt:
        items = [item for item in items if comparable_dt(item.created_at) <= end_dt]
    reverse = sort_order != "asc"
    items.sort(key=lambda item: (item.pinned, comparable_dt(item.created_at)), reverse=reverse)
    paged, pagination = page_slice(items, page, page_size)
    return ok({"items": [announcement_out(item) for item in paged], "pagination": pagination})


@router.post("/announcements")
def create_announcement(
    payload: AnnouncementCreate,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    ensure_teacher_or_admin(user)
    board = get_board_or_404(session, payload.board_id)
    item = Announcement(
        board_id=board.id,
        course_id=board.course_id,
        offering_id=board.offering_id,
        title=payload.title,
        content=payload.content,
        pinned=payload.pinned,
        popup=payload.popup,
        author_id=user.id,
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return ok(announcement_out(item))


@router.put("/announcements/{announcement_id}")
def update_announcement(
    announcement_id: int,
    payload: AnnouncementUpdate,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    item = session.get(Announcement, announcement_id)
    if not item or item.status == NoticeStatus.deleted:
        raise fail(404, 50101, "POST_NOT_FOUND")
    if not user.is_admin:
        ensure_author_or_admin(item.author_id, user)
    if payload.board_id is not None:
        board = get_board_or_404(session, payload.board_id)
        item.board_id = board.id
        item.course_id = board.course_id
        item.offering_id = board.offering_id
    for field in ("title", "content", "pinned", "popup", "status"):
        value = getattr(payload, field)
        if value is not None:
            setattr(item, field, value)
    item.updated_at = now()
    session.add(item)
    session.commit()
    session.refresh(item)
    return ok(announcement_out(item))


@router.delete("/announcements/{announcement_id}")
def delete_announcement(
    announcement_id: int,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    item = session.get(Announcement, announcement_id)
    if not item or item.status == NoticeStatus.deleted:
        raise fail(404, 50101, "POST_NOT_FOUND")
    if not user.is_admin:
        ensure_author_or_admin(item.author_id, user)
    item.status = NoticeStatus.deleted
    item.updated_at = now()
    session.add(item)
    session.commit()
    return ok(None)


@router.put("/announcements/{announcement_id}/popup_toggle")
def toggle_announcement_popup(
    announcement_id: int,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    ensure_teacher_or_admin(user)
    item = session.get(Announcement, announcement_id)
    if not item or item.status == NoticeStatus.deleted:
        raise fail(404, 50101, "POST_NOT_FOUND")
    item.popup = not item.popup
    item.updated_at = now()
    session.add(item)
    session.commit()
    return ok({"popup": item.popup})


@router.get("/posts")
def get_post_list(
    page: int = 1,
    page_size: int = 10,
    course_id: str | None = None,
    offering_id: str | None = None,
    board_id: int | None = None,
    module: PostModule | None = None,
    author_id: str | None = None,
    status: PostStatus | None = None,
    keyword: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    items = session.exec(select(ForumPost)).all()
    resolved_author_id = resolve_author_id(author_id, user)
    if course_id:
        items = [item for item in items if item.course_id == course_id]
    if offering_id:
        items = [item for item in items if item.offering_id == offering_id]
    if board_id:
        items = [item for item in items if item.board_id == board_id]
    if module:
        items = [item for item in items if item.module == module]
    if resolved_author_id is not None:
        items = [item for item in items if item.author_id == resolved_author_id]
    if status:
        items = [item for item in items if item.status == status]
    else:
        items = [item for item in items if item.status != PostStatus.deleted]
    if keyword:
        lowered = keyword.lower()
        items = [
            item
            for item in items
            if lowered in item.title.lower() or lowered in item.content.lower()
        ]
    reverse = sort_order != "asc"
    if sort_by == "hot_score":
        items.sort(key=lambda item: item.hot_score, reverse=reverse)
    else:
        items.sort(key=lambda item: (item.pinned, comparable_dt(item.created_at)), reverse=reverse)
    paged, pagination = page_slice(items, page, page_size)
    return ok({"items": [post_out(item) for item in paged], "pagination": pagination})


@router.post("/posts")
def create_post(
    payload: PostCreate,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    board = get_board_or_404(session, payload.board_id)
    status = PostStatus.pinned if payload.pinned else PostStatus.published
    item = ForumPost(
        board_id=board.id,
        course_id=payload.course_id or board.course_id,
        offering_id=payload.offering_id or board.offering_id,
        module=payload.module,
        title=payload.title,
        content=payload.content,
        status=status,
        pinned=payload.pinned,
        hot_score=10 if payload.pinned else 0,
        author_id=user.id,
        author_name=user.name,
        author_role=user.role,
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return ok(post_out(item))


@router.post("/posts/{post_id}/attachments")
def upload_attachment(
    post_id: int,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    post = session.get(ForumPost, post_id)
    if not post or post.status == PostStatus.deleted:
        raise fail(404, 50101, "POST_NOT_FOUND")
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename or "attachment").name
    stored_name = f"{uuid4().hex}_{safe_name}"
    stored_path = upload_dir / stored_name
    with stored_path.open("wb") as target:
        shutil.copyfileobj(file.file, target)
    attachment = ForumAttachment(
        post_id=post_id,
        file_name=safe_name,
        file_url=f"{settings.public_upload_prefix.rstrip('/')}/{stored_name}",
        file_size=stored_path.stat().st_size,
        mime_type=file.content_type or "application/octet-stream",
        uploader_id=user.id,
    )
    session.add(attachment)
    session.commit()
    session.refresh(attachment)
    return ok(attachment_out(attachment))


@router.get("/posts/{post_id}/attachments")
def list_post_attachments(
    post_id: int,
    session: Session = Depends(get_session),
) -> dict:
    post = session.get(ForumPost, post_id)
    if not post or post.status == PostStatus.deleted:
        raise fail(404, 50101, "POST_NOT_FOUND")
    items = session.exec(
        select(ForumAttachment).where(ForumAttachment.post_id == post_id)
    ).all()
    return ok({"items": [attachment_out(item) for item in items]})


@router.get("/posts/{post_id}/replies")
def get_reply_list(
    post_id: int,
    view: str = "tree",
    page: int = 1,
    page_size: int = 20,
    since_floor: int | None = None,
    session: Session = Depends(get_session),
) -> dict:
    post = session.get(ForumPost, post_id)
    if not post or post.status == PostStatus.deleted:
        raise fail(404, 50101, "POST_NOT_FOUND")
    items = session.exec(select(ForumReply).where(ForumReply.post_id == post_id)).all()
    items = [item for item in items if item.status != ReplyStatus.deleted]
    if since_floor is not None:
        items = [item for item in items if item.floor > since_floor]
    items.sort(key=lambda item: item.floor)
    if view == "tree":
        by_parent: dict[int | None, list[ForumReply]] = {}
        for item in items:
            by_parent.setdefault(item.parent_reply_id, []).append(item)

        def build(parent_id: int | None) -> list[dict]:
            result = []
            for child in by_parent.get(parent_id, []):
                data = reply_out(child)
                children = build(child.id)
                if children:
                    data["children"] = children
                result.append(data)
            return result

        return ok({"items": build(None)})
    paged, pagination = page_slice(items, page, page_size)
    return ok({"items": [reply_out(item) for item in paged], "pagination": pagination})


@router.post("/posts/{post_id}/replies")
def create_reply(
    post_id: int,
    payload: ReplyCreate,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    post = session.get(ForumPost, post_id)
    if not post or post.status == PostStatus.deleted:
        raise fail(404, 50101, "POST_NOT_FOUND")
    if payload.parent_reply_id is not None:
        parent = session.get(ForumReply, payload.parent_reply_id)
        if not parent or parent.post_id != post_id or parent.status == ReplyStatus.deleted:
            raise fail(404, 50301, "REPLY_NOT_FOUND")
    existing = session.exec(select(ForumReply).where(ForumReply.post_id == post_id)).all()
    item = ForumReply(
        post_id=post_id,
        floor=len(existing) + 1,
        parent_reply_id=payload.parent_reply_id,
        content=payload.content,
        author_id=user.id,
        author_name=user.name,
        author_role=user.role,
    )
    post.replies_count += 1
    post.hot_score = post.replies_count * 10 + post.likes_count * 3 + post.views_count * 0.1
    if post.hot_score >= 80 and post.status == PostStatus.published:
        post.status = PostStatus.hot
    session.add(item)
    session.add(post)
    session.commit()
    session.refresh(item)
    return ok(reply_out(item))


@router.get("/posts/{post_id}")
def get_post_detail(
    post_id: int,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    item = session.get(ForumPost, post_id)
    if not item or item.status == PostStatus.deleted:
        raise fail(404, 50101, "POST_NOT_FOUND")
    board = session.get(ForumBoard, item.board_id)
    item.views_count += 1
    item.hot_score = item.replies_count * 10 + item.likes_count * 3 + item.views_count * 0.1
    session.add(ForumViewLog(post_id=item.id, user_id=user.id, course_id=item.course_id))
    session.add(item)
    session.commit()
    session.refresh(item)
    return ok(post_out(item, board))


@router.put("/posts/{post_id}")
def update_post(
    post_id: int,
    payload: PostUpdate,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    item = session.get(ForumPost, post_id)
    if not item or item.status == PostStatus.deleted:
        raise fail(404, 50101, "POST_NOT_FOUND")
    if not user.is_admin:
        ensure_author_or_admin(item.author_id, user)
    if payload.board_id is not None:
        board = get_board_or_404(session, payload.board_id)
        item.board_id = board.id
        item.course_id = board.course_id
        item.offering_id = board.offering_id
    for field in ("title", "content", "module", "pinned", "status"):
        value = getattr(payload, field)
        if value is not None:
            setattr(item, field, value)
    if payload.pinned is not None and payload.status is None:
        item.status = PostStatus.pinned if payload.pinned else PostStatus.published
    item.updated_at = now()
    session.add(item)
    session.commit()
    session.refresh(item)
    return ok(post_out(item))


@router.delete("/posts/{post_id}")
def delete_post(
    post_id: int,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    item = session.get(ForumPost, post_id)
    if not item or item.status == PostStatus.deleted:
        raise fail(404, 50101, "POST_NOT_FOUND")
    if not user.is_admin:
        ensure_author_or_admin(item.author_id, user)
    item.status = PostStatus.deleted
    item.updated_at = now()
    replies = session.exec(select(ForumReply).where(ForumReply.post_id == post_id)).all()
    for reply in replies:
        reply.status = ReplyStatus.deleted
        reply.updated_at = now()
        session.add(reply)
    session.add(item)
    session.commit()
    return ok(None)


@router.delete("/attachments/{attachment_id}")
def delete_attachment(
    attachment_id: int,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    attachment = session.get(ForumAttachment, attachment_id)
    if not attachment:
        raise fail(404, 50001, "INVALID_PARAMS")
    if not user.is_admin and attachment.uploader_id != user.id:
        raise fail(403, 50002, "UNAUTHORIZED")
    prefix = settings.public_upload_prefix.rstrip("/") + "/"
    if attachment.file_url.startswith(prefix):
        local_path = Path(settings.upload_dir) / attachment.file_url.removeprefix(prefix)
        if local_path.exists():
            local_path.unlink()
    session.delete(attachment)
    session.commit()
    return ok(None)


@router.delete("/replies/{reply_id}")
def delete_reply(
    reply_id: int,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    item = session.get(ForumReply, reply_id)
    if not item or item.status == ReplyStatus.deleted:
        raise fail(404, 50301, "REPLY_NOT_FOUND")
    if not user.is_admin:
        ensure_author_or_admin(item.author_id, user)
    item.status = ReplyStatus.deleted
    item.updated_at = now()
    post = session.get(ForumPost, item.post_id)
    if post and post.replies_count > 0:
        post.replies_count -= 1
        post.hot_score = post.replies_count * 10 + post.likes_count * 3 + post.views_count * 0.1
        session.add(post)
    session.add(item)
    session.commit()
    return ok(None)


@router.get("/search/posts")
def search_posts(
    keyword: str = Query(min_length=1),
    page: int = 1,
    page_size: int = 10,
    course_id: str | None = None,
    offering_id: str | None = None,
    author_id: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    sort_by: str = "relevance",
    sort_order: str = "desc",
    session: Session = Depends(get_session),
) -> dict:
    lowered = keyword.strip().lower()
    if not lowered:
        raise fail(400, 50401, "KEYWORD_REQUIRED")
    posts = session.exec(select(ForumPost).where(ForumPost.status != PostStatus.deleted)).all()
    if course_id:
        posts = [item for item in posts if item.course_id == course_id]
    if offering_id:
        posts = [item for item in posts if item.offering_id == offering_id]
    if author_id:
        posts = [item for item in posts if item.author_id == author_id]
    start_dt = parse_date(start_date)
    end_dt = parse_date(end_date)
    if start_dt:
        posts = [item for item in posts if comparable_dt(item.created_at) >= start_dt]
    if end_dt:
        posts = [item for item in posts if comparable_dt(item.created_at) <= end_dt]
    matches = [
        item for item in posts if lowered in item.title.lower() or lowered in item.content.lower()
    ]
    reverse = sort_order != "asc"
    if sort_by == "hot_score":
        matches.sort(key=lambda item: item.hot_score, reverse=reverse)
    elif sort_by == "created_at":
        matches.sort(key=lambda item: comparable_dt(item.created_at), reverse=reverse)
    else:
        matches.sort(
            key=lambda item: (
                item.title.lower().count(lowered) * 3 + item.content.lower().count(lowered),
                item.hot_score,
            ),
            reverse=True,
        )
    paged, pagination = page_slice(matches, page, page_size)
    return ok(
        {
            "items": [
                {
                    "id": item.id,
                    "title": item.title,
                    "snippet": item.content[:180],
                    "course_id": item.course_id,
                    "board_id": item.board_id,
                    "author_id": item.author_id,
                    "created_at": dt(item.created_at),
                    "hot_score": item.hot_score,
                }
                for item in paged
            ],
            "pagination": pagination,
        }
    )


@router.get("/stats/hot_posts")
def get_hot_posts(
    period: str,
    limit: int = 10,
    course_id: str | None = None,
    offering_id: str | None = None,
    session: Session = Depends(get_session),
) -> dict:
    items = session.exec(select(ForumPost).where(ForumPost.status != PostStatus.deleted)).all()
    if course_id:
        items = [item for item in items if item.course_id == course_id]
    if offering_id:
        items = [item for item in items if item.offering_id == offering_id]
    start, _ = period_bounds(period)
    start_dt = parse_date(start)
    if start_dt:
        items = [item for item in items if comparable_dt(item.created_at) >= start_dt]
    items.sort(key=lambda item: item.hot_score, reverse=True)
    return ok(
        {
            "items": [
                {
                    "id": item.id,
                    "title": item.title,
                    "course_id": item.course_id,
                    "board_id": item.board_id,
                    "author_id": item.author_id,
                    "replies_count": item.replies_count,
                    "likes_count": item.likes_count,
                    "hot_score": item.hot_score,
                    "created_at": dt(item.created_at),
                }
                for item in items[:limit]
            ]
        }
    )


@router.get("/stats/user_activity")
def get_user_activity(
    period: str,
    user_id: int | None = None,
    course_id: str | None = None,
    offering_id: str | None = None,
    session: Session = Depends(get_session),
) -> dict:
    items = activity_items(session, course_id, offering_id, period)
    if user_id:
        items = [item for item in items if item["user_id"] == user_id]
    return ok({"items": items})


@router.get("/internal/forum/activity")
def get_forum_activity(
    period: str,
    course_id: str | None = None,
    offering_id: str | None = None,
    session: Session = Depends(get_session),
) -> dict:
    return ok({"data": activity_items(session, course_id, offering_id, period)})


@router.post("/forum/activity-batch")
def push_activity_batch(
    payload: ActivityBatchForm,
    session: Session = Depends(get_session),
) -> dict:
    outbox = ActivityBatchOutbox(
        course_id=payload.course_id,
        period_start=payload.period_start,
        period_end=payload.period_end,
        payload_json=json.dumps(payload.model_dump(), ensure_ascii=False),
    )
    session.add(outbox)
    session.commit()
    session.refresh(outbox)
    return ok({"outbox_id": outbox.id, "status": outbox.status})


@router.get("/moderation")
def list_moderation_items(
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    course_name: str | None = None,
    target_type: ModerationTargetType | None = None,
    status: ModerationStatus | None = None,
    session: Session = Depends(get_session),
) -> dict:
    items = session.exec(select(ForumModeration)).all()
    if keyword:
        lowered = keyword.lower()
        items = [
            item
            for item in items
            if lowered in item.title.lower()
            or lowered in item.content.lower()
            or lowered in item.author_name.lower()
            or lowered in item.reporter_name.lower()
            or lowered in item.reason.lower()
        ]
    if course_name:
        items = [item for item in items if item.course_name == course_name]
    if target_type:
        items = [item for item in items if item.target_type == target_type]
    if status:
        items = [item for item in items if item.status == status]
    items.sort(key=lambda item: item.created_at, reverse=True)
    paged, pagination = page_slice(items, page, page_size)
    return ok({"items": [moderation_out(item) for item in paged], "pagination": pagination})


@router.post("/moderation/reports")
def create_moderation_report(
    payload: ModerationReportCreate,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    item = build_moderation_from_target(
        session=session,
        target_type=payload.target_type,
        target_id=payload.target_id,
        reporter_name=payload.reporter_name or user.name,
        reason=payload.reason,
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return ok(moderation_out(item))


@router.put("/moderation/{moderation_id}/handle")
def handle_moderation_item(
    moderation_id: int,
    payload: ModerationHandleForm,
    session: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    if not user.is_admin:
        raise fail(403, 50002, "UNAUTHORIZED")
    item = session.get(ForumModeration, moderation_id)
    if not item:
        raise fail(404, 50001, "INVALID_PARAMS")

    item.status = payload.status
    if payload.reason:
        item.reason = payload.reason
    item.handled_at = now()
    item.handler_name = user.name

    if item.target_type == ModerationTargetType.post:
        post = session.get(ForumPost, item.target_id)
        if post and payload.status in {ModerationStatus.hidden, ModerationStatus.deleted}:
            post.status = PostStatus(payload.status.value)
            post.updated_at = now()
            session.add(post)
        elif (
            post
            and payload.status == ModerationStatus.approved
            and post.status == PostStatus.hidden
        ):
            post.status = PostStatus.published
            post.updated_at = now()
            session.add(post)
    else:
        reply = session.get(ForumReply, item.target_id)
        if reply and payload.status in {ModerationStatus.hidden, ModerationStatus.deleted}:
            reply.status = ReplyStatus(payload.status.value)
            reply.updated_at = now()
            session.add(reply)
        elif (
            reply
            and payload.status == ModerationStatus.approved
            and reply.status == ReplyStatus.hidden
        ):
            reply.status = ReplyStatus.published
            reply.updated_at = now()
            session.add(reply)

    session.add(item)
    session.commit()
    session.refresh(item)
    return ok(moderation_out(item))
