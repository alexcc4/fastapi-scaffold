from unittest.mock import patch

from httpx import ASGITransport, AsyncClient

from app.core.request_context import get_request_context
from app.main import app, create_app


async def test_invalid_request_id_is_replaced(
    base_client: AsyncClient,
) -> None:
    response = await base_client.get(
        "/ping",
        headers={"X-Request-ID": "invalid request id"},
    )

    request_id = response.headers["x-request-id"]
    assert request_id != "invalid request id"
    assert len(request_id) == 32


async def test_access_log_omits_sensitive_request_data() -> None:
    with patch(
        "app.middlewares.request_observability.ACCESS_LOGGER.info"
    ) as log:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/missing?secret=query-value",
                headers={
                    "Authorization": "Bearer raw-secret-token",
                    "Cookie": "session=cookie-secret",
                },
            )

    assert response.status_code == 404
    log.assert_called_once()
    logged = log.call_args.args[0] % log.call_args.args[1:]
    assert "path='/missing'" in logged
    assert "query-value" not in logged
    assert "raw-secret-token" not in logged
    assert "cookie-secret" not in logged
    assert get_request_context() is None


async def test_ping_does_not_write_access_log(
    base_client: AsyncClient,
) -> None:
    with patch(
        "app.middlewares.request_observability.ACCESS_LOGGER.info"
    ) as log:
        response = await base_client.get("/ping")

    assert response.status_code == 200
    log.assert_not_called()


async def test_unhandled_error_keeps_observability_headers() -> None:
    test_app = create_app()

    @test_app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("boom")

    with patch(
        "app.middlewares.request_observability.ACCESS_LOGGER.info"
    ) as log:
        async with AsyncClient(
            transport=ASGITransport(
                app=test_app,
                raise_app_exceptions=False,
            ),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/boom",
                headers={"X-Request-ID": "boom-123"},
            )

    assert response.status_code == 500
    assert response.headers["x-request-id"] == "boom-123"
    assert response.headers["server-timing"].startswith("app;dur=")
    log.assert_called_once()
    logged = log.call_args.args[0] % log.call_args.args[1:]
    assert "status=500" in logged
    assert get_request_context() is None
