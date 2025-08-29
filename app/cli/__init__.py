import typer

from app.core.logging import setup_logging
from .init_user import create_user_command

app = typer.Typer(help="FastAPI CLI Tools")

app.command("create-user", help="create new user")(create_user_command)


@app.callback()
def main():
    """cli entrypoint"""
    setup_logging()