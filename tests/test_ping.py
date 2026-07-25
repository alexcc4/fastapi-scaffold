from httpx import AsyncClient


async def test_ping(base_client: AsyncClient) -> None:
    response = await base_client.get("/ping")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["x-request-id"]
    assert response.headers["server-timing"].startswith("app;dur=")
