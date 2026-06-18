from app.integrations.base import InternalServiceClient
from app.schemas import ExternalCheckResult


class CourseSelectClient(InternalServiceClient):
    async def check_enrollment(
        self,
        user_id: int,
        course_id: str,
        offering_id: str | None,
    ) -> ExternalCheckResult:
        data = await self.get(
            "/api/v1/course-selection/enrollments/check",
            {"user_id": user_id, "course_id": course_id, "offering_id": offering_id},
        )
        return ExternalCheckResult(allowed=bool(data.get("data", {}).get("allowed")), raw=data)

    async def check_teacher(
        self,
        user_id: int,
        course_id: str,
        offering_id: str | None,
    ) -> ExternalCheckResult:
        data = await self.get(
            "/api/v1/course-selection/teachers/check",
            {"user_id": user_id, "course_id": course_id, "offering_id": offering_id},
        )
        return ExternalCheckResult(allowed=bool(data.get("data", {}).get("allowed")), raw=data)
