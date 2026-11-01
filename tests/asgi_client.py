"""A tiny dependency-free ASGI test client (no httpx needed)."""

from __future__ import annotations

import asyncio
import json as jsonlib
from collections.abc import Iterable
from typing import Any


class Response:
    def __init__(self, status: int, headers: dict[str, str], body: bytes) -> None:
        self.status_code = status
        self.headers = headers
        self.body = body

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")

    def json(self) -> Any:
        return jsonlib.loads(self.body)


class ASGIClient:
    def __init__(self, app: Any, client_ip: str = "203.0.113.9") -> None:
        self.app = app
        self.client_ip = client_ip

    def request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        body: bytes | Iterable[bytes] | None = None,
        headers: dict[str, str] | None = None,
        client_ip: str | None = None,
    ) -> Response:
        return asyncio.run(self._request(method, path, json, body, headers or {}, client_ip or self.client_ip))

    def get(self, path: str, **kwargs: Any) -> Response:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> Response:
        return self.request("POST", path, **kwargs)

    async def _request(
        self, method: str, path: str, json: Any, body: Any, headers: dict[str, str], client_ip: str
    ) -> Response:
        chunks: list[bytes]
        send_length = True
        if json is not None:
            chunks = [jsonlib.dumps(json).encode()]
            headers = {"content-type": "application/json", **headers}
        elif body is None:
            chunks = [b""]
        elif isinstance(body, bytes):
            chunks = [body]
        else:
            chunks = list(body)
            send_length = False  # simulate chunked upload without a Content-Length header

        raw_headers = [(b"host", b"testserver")]
        raw_headers += [(k.lower().encode(), v.encode()) for k, v in headers.items()]
        if send_length and method in {"POST", "PUT", "PATCH"}:
            raw_headers.append((b"content-length", str(sum(len(c) for c in chunks)).encode()))

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "root_path": "",
            "headers": raw_headers,
            "client": (client_ip, 50000),
            "server": ("testserver", 80),
        }

        pending = list(chunks)

        async def receive() -> dict[str, Any]:
            if pending:
                chunk = pending.pop(0)
                return {"type": "http.request", "body": chunk, "more_body": bool(pending)}
            await asyncio.sleep(0)
            return {"type": "http.disconnect"}

        status = 500
        response_headers: dict[str, str] = {}
        parts: list[bytes] = []

        async def send(message: dict[str, Any]) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                response_headers.update({k.decode().lower(): v.decode() for k, v in message["headers"]})
            elif message["type"] == "http.response.body":
                parts.append(message.get("body", b""))

        await self.app(scope, receive, send)
        return Response(status, response_headers, b"".join(parts))
