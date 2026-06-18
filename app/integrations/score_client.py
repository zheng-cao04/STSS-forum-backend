import httpx

from app.integrations.base import InternalServiceClient


class ScoreMgmtClient(InternalServiceClient):
    async def push_activity_batch(self, payload: dict) -> dict:
        async with httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=httpx.Timeout(5.0, read=20.0),
        ) as client:
            response = await client.post("/api/v1/grade/forum/activity-batch", json=payload)
            response.raise_for_status()
            return response.json()
