from app.integrations.base import InternalServiceClient


class InfoMgmtClient(InternalServiceClient):
    async def get_user(self, user_id: int) -> dict:
        return await self.get(f"/api/v1/info/users/{user_id}")
