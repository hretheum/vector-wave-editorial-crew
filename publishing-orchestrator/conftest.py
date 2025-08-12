import asyncio
import pytest
import httpx

BASE_URL = "http://localhost:8080"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def publication_id():
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(f"{BASE_URL}/test/simple", timeout=10.0)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("publication_id")
        except Exception:
            pass
    return None
