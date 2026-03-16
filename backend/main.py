"""
Brickfolio AI Real Estate — FastAPI entry point
Wires together all route modules.
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from routes.properties     import router as properties_router
from routes.users          import router as users_router
from routes.recommendtaions import router as recommendations_router

app = FastAPI(
    title       = "Brickfolio AI API",
    description = "Pune's #1 Zero Brokerage Real Estate Platform — AI Recommendation Engine",
    version     = "2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins  = ["*"],
    allow_methods  = ["*"],
    allow_headers  = ["*"],
)

# ─── Register Routers ─────────────────────────────────────────────────────
app.include_router(properties_router)
app.include_router(users_router)
app.include_router(recommendations_router)

# ─── Serve frontend statically (optional) ─────────────────────────────────
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/app", include_in_schema=False)
    async def serve_frontend():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


# ─── Health check ─────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
async def root():
    return {
        "status":  "running",
        "version": "2.0.0",
        "docs":    "/docs",
        "app":     "/app",
    }

@app.get("/health", tags=["Health"])
async def health():
    from database import db
    try:
        db.command("ping")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {e}"
    return {"api": "ok", "database": db_status}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"\n🏠  Brickfolio AI  →  http://localhost:{port}")
    print(f"📖  API Docs       →  http://localhost:{port}/docs\n")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)