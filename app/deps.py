from dataclasses import dataclass

from fastapi import Header


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


def get_current_user(
    x_user_id: str | None = Header(default=None),
    x_user_role: str | None = Header(default=None),
    x_user_name: str | None = Header(default=None),
) -> CurrentUser:
    return CurrentUser(
        id=int(x_user_id or 1),
        role=(x_user_role or "teacher").lower(),
        name=x_user_name or "开发教师",
    )
