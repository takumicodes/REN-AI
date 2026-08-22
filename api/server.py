"""
REN-AI FastAPI Server Application
Configures CORS, API routers, static file delivery for the mobile web client, and startup banner.
"""

import os
import sys
import socket
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse

from api.auth import require_auth
from api.routes.auth import router as auth_router
from api.routes.status import router as status_router
from api.routes.conversations import router as conversations_router
from api.routes.skills import router as skills_router
from api.routes.tts import router as tts_router
from api.routes.chat import router as chat_router
from api.routes.dream import router as dream_router
from api.routes.vision import router as vision_router
from ren.config.settings import settings
from ren.monitoring.logger import agent_logger

ROOT_DIR = Path(__file__).resolve().parent.parent
MOBILE_DIR = ROOT_DIR / "mobile"


def get_local_ip() -> str:
    """Detects local LAN IP address for phone connectivity."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context for server startup & shutdown events."""
    local_ip = get_local_ip()
    port = int(os.getenv("REN_SERVER_PORT", "8000"))
    
    print("\n" + "=" * 62)
    print(" 🪐 REN-AI MOBILE & WEB SERVER ONLINE")
    print("=" * 62)
    print(f"  • Local Desktop Access : http://localhost:{port}")
    print(f"  • Phone / Wi-Fi Access : http://{local_ip}:{port}")
    print(f"  • API Documentation    : http://localhost:{port}/docs")
    print("=" * 62 + "\n")
    
    agent_logger.info(f"REN API Server started on http://{local_ip}:{port}")
    yield
    agent_logger.info("REN API Server shutting down...")


def create_app() -> FastAPI:
    """Factory creating and configuring the FastAPI instance."""
    app = FastAPI(
        title="REN-AI Assistant API",
        description="REST & Streaming API for REN-AI Autonomous Assistant",
        version=settings.VERSION,
        lifespan=lifespan,
    )

    # Enable CORS for cross-origin or local network mobile requests
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register Public Auth Router
    app.include_router(auth_router, prefix="/api")

    # Register Protected API Routers (enforces auth if access key configured)
    app.include_router(status_router, prefix="/api", dependencies=[Depends(require_auth)])
    app.include_router(chat_router, prefix="/api", dependencies=[Depends(require_auth)])
    app.include_router(conversations_router, prefix="/api", dependencies=[Depends(require_auth)])
    app.include_router(skills_router, prefix="/api", dependencies=[Depends(require_auth)])
    app.include_router(tts_router, prefix="/api", dependencies=[Depends(require_auth)])
    app.include_router(dream_router, prefix="/api", dependencies=[Depends(require_auth)])
    app.include_router(vision_router, prefix="/api", dependencies=[Depends(require_auth)])

    # Serve Mobile Web Client static files & PWA assets
    if MOBILE_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(MOBILE_DIR)), name="mobile_static")

        @app.get("/manifest.json")
        async def serve_manifest():
            manifest_file = MOBILE_DIR / "manifest.json"
            if manifest_file.exists():
                return FileResponse(str(manifest_file), media_type="application/manifest+json")
            return {}

        @app.get("/sw.js")
        async def serve_sw():
            sw_file = MOBILE_DIR / "sw.js"
            if sw_file.exists():
                return FileResponse(str(sw_file), media_type="application/javascript")
            return ""

        @app.get("/")
        async def serve_root():
            index_file = MOBILE_DIR / "index.html"
            if index_file.exists():
                return FileResponse(str(index_file))
            return {"status": "REN-AI API running. Mobile frontend missing index.html"}

        @app.get("/mobile")
        async def serve_mobile_redirect():
            return RedirectResponse(url="/")
    else:
        @app.get("/")
        async def serve_root_fallback():
            return {"status": "REN-AI API running", "version": settings.VERSION}

    return app


app = create_app()
