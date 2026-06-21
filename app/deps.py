import base64
import json
from dataclasses import dataclass
from urllib.parse import unquote

from fastapi import Header

DEV_TOKEN_IDENTITY: dict[str, tuple[int, str, str]] = {
    "token-student": (7, "student", "学生用户"),
    "token-teacher": (2, "teacher", "教师用户"),
    "token-academic-admin": (1, "admin", "教务管理员"),
}


@dataclass(frozen=True)
class CurrentUser:
    id: int
    role: str
    name: str

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_teacher_or_admin(self) -> bool:
        return self.role in {"teacher", "admin"}


def decode_jwt_payload(token: str | None) -> dict:
    if not token or token.count(".") < 2:
        return {}
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        raw = base64.urlsafe_b64decode(payload.encode("utf-8"))
        return json.loads(raw)
    except (ValueError, json.JSONDecodeError):
        return {}


def normalize_role(role: str | None) -> str:
    normalized = (role or "").strip().lower()
    if normalized in {"academic_admin", "academic-admin", "academicadmin", "sys_admin"}:
        return "admin"
    if normalized in {"student", "teacher", "admin"}:
        return normalized
    return "teacher"


def parse_user_id(value: str | int | None) -> int | None:
    if value in {None, ""}:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def get_current_user(
    x_user_id: str | None = Header(default=None),
    x_user_role: str | None = Header(default=None),
    x_user_name: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
    x_access_token: str | None = Header(default=None),
) -> CurrentUser:
    token = x_access_token or (authorization or "").removeprefix("Bearer ").strip()
    mapped = DEV_TOKEN_IDENTITY.get(token)
    jwt_payload = decode_jwt_payload(token)

    user_id = parse_user_id(x_user_id)
    if user_id is None and mapped:
        user_id = mapped[0]
    if user_id is None:
        user_id = parse_user_id(
            jwt_payload.get("sub")
            or jwt_payload.get("id")
            or jwt_payload.get("user_id")
            or jwt_payload.get("userId")
        )

    role = normalize_role(
        x_user_role
        or (mapped[1] if mapped else None)
        or jwt_payload.get("role")
        or jwt_payload.get("user_role")
        or jwt_payload.get("userRole")
    )
    raw_name = (
        x_user_name
        or (mapped[2] if mapped else None)
        or jwt_payload.get("name")
        or jwt_payload.get("username")
    )

    return CurrentUser(
        id=user_id or 1,
        role=role,
        name=unquote(str(raw_name or "开发教师")),
    )
