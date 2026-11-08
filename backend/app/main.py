"""
STOCK UNDO! - Centralized TallyPrime Stock Viewer Backend
"Check stock before you call the godown!"
"""

import asyncio
import collections
from contextlib import asynccontextmanager
import time
from typing import Dict
from fastapi import FastAPI, Header, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.routes.health import router as health_router
from app.routes.stock import router as stock_router
from app.routes.ws import router as ws_router, background_stock_sync_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start live stock monitoring background task
    sync_task = asyncio.create_task(background_stock_sync_loop())
    yield
    sync_task.cancel()
    try:
        await sync_task
    except asyncio.CancelledError:
        pass


# ---------------------------------------------------------------------------
# Simple In-Memory Rate Limiter (Token Bucket per IP)
# ---------------------------------------------------------------------------
class SimpleRateLimiter:
    def __init__(self, requests_per_minute: int = 300):
        self.rpm = requests_per_minute
        self.hits: Dict[str, collections.deque] = collections.defaultdict(collections.deque)

    def is_rate_limited(self, client_ip: str) -> bool:
        now = time.time()
        minute_ago = now - 60.0
        q = self.hits[client_ip]

        # Purge timestamps older than 1 minute
        while q and q[0] < minute_ago:
            q.popleft()

        if len(q) >= self.rpm:
            return True

        q.append(now)
        return False


rate_limiter = SimpleRateLimiter(requests_per_minute=settings.RATE_LIMIT_PER_MINUTE)

# ---------------------------------------------------------------------------
# FastAPI Application Factory
# ---------------------------------------------------------------------------
app = FastAPI(
    title=f"{settings.APP_NAME} API",
    description=f"### {settings.TAGLINE}\n\nStrictly read-only stock viewer connecting to TallyPrime instances on PC 1 and PC 2.",
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ---------------------------------------------------------------------------
# Middleware: CORS
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Middleware: Security Headers & Rate Limiting
# ---------------------------------------------------------------------------
@app.middleware("http")
async def security_and_rate_limit_middleware(request: Request, call_next):
    # Rate Limiting
    client_ip = request.client.host if request.client else "127.0.0.1"
    if rate_limiter.is_rate_limited(client_ip):
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Too many requests. Please slow down."},
        )

    # Optional Authentication Guard for Cloudflare Ingress
    if settings.REQUIRE_AUTH and request.url.path.startswith("/api/stock"):
        token = request.headers.get("X-Staff-Token") or request.query_params.get("token")
        if not token or token != settings.STAFF_ACCESS_TOKEN:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid or missing staff authentication token."},
            )

    response: Response = await call_next(request)

    # Security Headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(health_router, prefix="/api")
app.include_router(stock_router, prefix="/api")
app.include_router(ws_router, prefix="/api")


@app.get("/", tags=["Root"])
async def root():
    return {
        "app": settings.APP_NAME,
        "tagline": settings.TAGLINE,
        "status": "operational",
        "endpoints": {
            "health": "/api/health",
            "tally_status": "/api/tally/status",
            "all_stock": "/api/stock/all",
            "pc1_stock": "/api/stock/pc1",
            "pc2_stock": "/api/stock/pc2",
            "search_stock": "/api/stock/search?q={query}",
            "whitelist": "/api/stock/whitelist",
            "docs": "/api/docs",
        },
    }

