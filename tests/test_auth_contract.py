from app.main import app


def test_auth_openapi_declares_error_responses_and_headers() -> None:
    paths = app.openapi()["paths"]
    operations = (
        paths["/api/auth/token"]["post"],
        paths["/api/auth/me"]["get"],
        paths["/api/auth/logout"]["post"],
    )

    for operation in operations:
        assert {"401", "503"} <= operation["responses"].keys()
        assert "WWW-Authenticate" in operation["responses"]["401"]["headers"]

    assert (
        "Cache-Control"
        in paths["/api/auth/token"]["post"]["responses"]["200"]["headers"]
    )
