from app.integrations.base import InternalServiceClient
from app.schemas import ExternalCheckResult


class CourseSelectClient(InternalServiceClient):
    async def list_student_enrollments(
        self,
        student_id: str,
        semester: str,
        status: str = "enrolled",
        requester_id: str | None = None,
        requester_role: str = "admin",
    ) -> dict:
        """C 组给 D 组的稳定契约：查询学生选课列表。"""
        return await self.get(
            f"/api/course-selection/v1/students/{student_id}/enrollments",
            {"semester": semester, "status": status},
            {
                "X-User-Id": requester_id or student_id,
                "X-User-Role": requester_role,
            },
        )

    async def get_roster(
        self,
        offering_id: str,
        include_dropped: bool = False,
        requester_id: str = "forum-service",
        requester_role: str = "admin",
    ) -> dict:
        """C 组给 F 组的花名册契约；D 组可用于课程板块成员校验。"""
        return await self.get(
            f"/api/course-selection/v1/offerings/{offering_id}/roster",
            {"include_dropped": include_dropped},
            {
                "X-User-Id": requester_id,
                "X-User-Role": requester_role,
            },
        )

    async def check_enrollment(
        self,
        user_id: int | str,
        course_id: str | None,
        offering_id: str | None,
        semester: str = "2026-1",
    ) -> ExternalCheckResult:
        """Return whether a student is enrolled in the target course/offering."""
        data = await self.list_student_enrollments(
            student_id=str(user_id),
            semester=semester,
            status="enrolled",
            requester_id=str(user_id),
            requester_role="student",
        )
        rows = data.get("data", {}).get("list", [])
        allowed = any(
            (offering_id and item.get("offering_id") == offering_id)
            or (course_id and item.get("course_code") == course_id)
            for item in rows
        )
        return ExternalCheckResult(allowed=allowed, raw=data)

    async def check_teacher(
        self,
        user_id: int | str,
        course_id: str,
        offering_id: str | None,
    ) -> ExternalCheckResult:
        """Best-effort teacher/admin check using C 组 roster endpoint when offering_id exists."""
        if not offering_id:
            return ExternalCheckResult(allowed=False, reason="offering_id required")
        data = await self.get_roster(
            offering_id=offering_id,
            include_dropped=False,
            requester_id=str(user_id),
            requester_role="teacher",
        )
        returned_course = data.get("data", {}).get("course_code")
        return ExternalCheckResult(allowed=returned_course in {None, "", course_id}, raw=data)
