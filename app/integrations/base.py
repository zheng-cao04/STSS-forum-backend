import httpx


class InternalServiceClient:
    def __init__(self, base_url: str, internal_token: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {internal_token}"}

    async def get(self, path: str, params: dict | None = None) -> dict:
        async with httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=httpx.Timeout(5.0, read=15.0),
        ) as client:
            response = await client.get(path, params=params)
            response.raise_for_status()
            return response.json()
