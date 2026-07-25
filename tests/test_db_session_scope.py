from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1] / "app"
ALLOWED_PATH = APP_ROOT / "api" / "deps.py"
FORBIDDEN = "Depends(get_db"


def test_http_db_injection_uses_shared_dbsession_alias() -> None:
    offenders: list[str] = []
    for path in APP_ROOT.rglob("*.py"):
        if path == ALLOWED_PATH:
            continue
        text = path.read_text(encoding="utf-8")
        if FORBIDDEN in text:
            offenders.append(str(path.relative_to(APP_ROOT.parent)))

    assert offenders == [], (
        "HTTP code must inject DbSession from app.api.deps instead of "
        f"Depends(get_db...); found in: {offenders}"
    )
