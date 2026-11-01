"""HTTP layer: a small Starlette app serving the JSON API and the static front end."""

from __future__ import annotations

import logging
import math
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from . import __version__
from .ai import AssistantService
from .config import PROJECT_ROOT, Settings, get_settings
from .models import ChatRequest, ChatResponse, IdeasResponse, PlanRequest
from .planner import InvalidEventDate, build_plan
from .security import BodySizeLimitMiddleware, RateLimiter, SecurityHeadersMiddleware

logger = logging.getLogger("celebration_planner")

STATIC_DIR = PROJECT_ROOT / "static"
ModelT = TypeVar("ModelT", bound=BaseModel)


def _json_error(status: int, message: str, headers: dict[str, str] | None = None) -> JSONResponse:
    return JSONResponse({"detail": message}, status_code=status, headers=headers)


def _field_error(field: str, message: str) -> JSONResponse:
    return JSONResponse({"detail": [{"loc": [field], "msg": message}]}, status_code=422)


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


async def _parse(request: Request, model: type[ModelT]) -> ModelT | Response:
    """Parse and validate a JSON body. Returns the model, or an error response to send back."""
    try:
        payload: Any = await request.json()
    except ValueError:
        return _json_error(400, "Request body must be valid JSON.")
    try:
        return model.model_validate(payload)
    except ValidationError as exc:
        errors = [
            {"loc": list(err["loc"]), "msg": err["msg"]}
            for err in exc.errors(include_url=False, include_context=False, include_input=False)
        ]
        return JSONResponse({"detail": errors}, status_code=422)


def create_app(settings: Settings | None = None, assistant: AssistantService | None = None) -> Starlette:
    settings = settings or get_settings()
    assistant = assistant or AssistantService(settings)
    limiters = {
        "general": RateLimiter(settings.rate_limit_per_minute),
        "ai": RateLimiter(settings.ai_rate_limit_per_minute),
    }

    def throttled(kind: str, request: Request) -> Response | None:
        retry_after = limiters[kind].check(_client_key(request))
        if retry_after:
            return _json_error(
                429,
                "Too many requests. Please wait a moment and try again.",
                headers={"Retry-After": str(math.ceil(retry_after))},
            )
        return None

    async def health(request: Request) -> Response:
        return JSONResponse({"status": "ok", "version": __version__, "ai_enabled": assistant.ai_enabled})

    async def plan_endpoint(request: Request) -> Response:
        if (blocked := throttled("general", request)) is not None:
            return blocked
        parsed = await _parse(request, PlanRequest)
        if isinstance(parsed, Response):
            return parsed
        try:
            plan = build_plan(parsed)
        except InvalidEventDate as exc:
            return _field_error("event_date", str(exc))
        return JSONResponse(plan.model_dump(mode="json"))

    async def ideas_endpoint(request: Request) -> Response:
        if (blocked := throttled("ai", request)) is not None:
            return blocked
        parsed = await _parse(request, PlanRequest)
        if isinstance(parsed, Response):
            return parsed
        ideas, source = await assistant.ideas(parsed)
        return JSONResponse(IdeasResponse(ideas=ideas, source=source).model_dump(mode="json"))  # type: ignore[arg-type]

    async def chat_endpoint(request: Request) -> Response:
        if (blocked := throttled("ai", request)) is not None:
            return blocked
        parsed = await _parse(request, ChatRequest)
        if isinstance(parsed, Response):
            return parsed
        try:
            plan = build_plan(parsed.plan)
        except InvalidEventDate as exc:
            return _field_error("event_date", str(exc))
        answer, source = await assistant.chat(parsed.plan, plan, parsed.question)
        return JSONResponse(ChatResponse(answer=answer, source=source).model_dump(mode="json"))  # type: ignore[arg-type]

    api_methods = {"/api/health": "GET, HEAD", "/api/plan": "POST", "/api/ideas": "POST", "/api/chat": "POST"}

    async def api_fallback(request: Request) -> Response:
        """Reached only when no API route matched: wrong method on a known path, or an unknown path."""
        allowed = api_methods.get(request.url.path)
        if allowed:
            return _json_error(405, "Method not allowed.", headers={"Allow": allowed})
        return _json_error(404, "Not found.")

    async def unexpected_error(request: Request, exc: Exception) -> Response:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return _json_error(500, "Something went wrong on our side. Please try again.")

    return Starlette(
        routes=[
            Route("/api/health", health, methods=["GET"]),
            Route("/api/plan", plan_endpoint, methods=["POST"]),
            Route("/api/ideas", ideas_endpoint, methods=["POST"]),
            Route("/api/chat", chat_endpoint, methods=["POST"]),
            Route(
                "/api/{rest:path}",
                api_fallback,
                methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            ),
            Mount("/", app=StaticFiles(directory=STATIC_DIR, html=True), name="static"),
        ],
        middleware=[
            Middleware(SecurityHeadersMiddleware),
            Middleware(BodySizeLimitMiddleware, max_bytes=settings.max_body_bytes),
        ],
        exception_handlers={Exception: unexpected_error},
    )


app = create_app()
