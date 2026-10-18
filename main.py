import os
import time
import uuid
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

app = FastAPI()

EMAIL = "pujarangaraj356@gmail.com"
ALLOWED_ORIGIN = "https://app-qade20.example.com"

RATE_LIMIT = 14
WINDOW_SECONDS = 10

# Per-client request timestamps
client_requests = defaultdict(deque)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.middleware("http")
async def cors_middleware(request: Request, call_next):
    origin = request.headers.get("origin")

    if request.method == "OPTIONS" and request.url.path == "/ping":
        if origin == ALLOWED_ORIGIN:
            response = Response(status_code=204)
            response.headers["Access-Control-Allow-Origin"] = ALLOWED_ORIGIN
            response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = (
                "X-Request-ID, X-Client-ID, Content-Type"
            )
            response.headers["Access-Control-Max-Age"] = "600"
            response.headers["Vary"] = "Origin"
            return response

        return Response(status_code=403)

    response = await call_next(request)

    if origin == ALLOWED_ORIGIN:
        response.headers["Access-Control-Allow-Origin"] = ALLOWED_ORIGIN
        response.headers["Vary"] = "Origin"

    return response


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path != "/ping":
        return await call_next(request)

    client_id = request.headers.get("X-Client-ID")
    if not client_id:
        client_id = request.client.host if request.client else "unknown"

    now = time.monotonic()
    timestamps = client_requests[client_id]

    while timestamps and now - timestamps[0] >= WINDOW_SECONDS:
        timestamps.popleft()

    if len(timestamps) >= RATE_LIMIT:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
        )

    timestamps.append(now)
    return await call_next(request)


@app.get("/ping")
async def ping(request: Request):
    return {
        "email": EMAIL,
        "request_id": request.state.request_id,
    }