"""ASGI entrypoint for the DCA bot."""

from app.core.app import create_app


app = create_app()
