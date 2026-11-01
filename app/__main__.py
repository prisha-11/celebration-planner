"""Run the app with ``python -m app`` (HOST and PORT can be set via environment variables)."""

import os

import uvicorn


def main() -> None:
    host = os.getenv("HOST", "127.0.0.1")
    try:
        port = int(os.getenv("PORT", "8000"))
    except ValueError:
        port = 8000
    uvicorn.run("app.main:app", host=host, port=port)


if __name__ == "__main__":
    main()
