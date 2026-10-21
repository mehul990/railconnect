from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.seed import seed_database
from app.routers import auth, trains, bookings, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager: initialize tables and seed data upon startup."""
    seed_database()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="A modern, high-reliability railway reservation backend featuring JWT authentication, role-based admin controls, dynamic inventory management, and concurrency-safe ticket booking.",
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for developer convenience
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers under /api/v1
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(trains.router, prefix=settings.API_V1_STR)
app.include_router(bookings.router, prefix=settings.API_V1_STR)
app.include_router(admin.router, prefix=settings.API_V1_STR)

# Mount frontend web application at /ui
from fastapi.staticfiles import StaticFiles
from pathlib import Path

frontend_path = Path("frontend")
if frontend_path.exists():
    app.mount("/ui", StaticFiles(directory="frontend", html=True), name="frontend")


@app.get("/", tags=["Health & Status"])
def root():
    """System information and operational status."""
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "online",
        "documentation": "/docs",
        "frontend_ui": "/ui",
        "vercel_deployment": "https://railconnect-mehul.vercel.app",
        "api_v1_base": settings.API_V1_STR,
        "message": "Welcome to RailConnect API. Browse /docs for interactive Swagger API testing, or /ui for the interactive web frontend."
    }


@app.get("/health", tags=["Health & Status"])
def health_check():
    """Health check endpoint for liveness monitoring."""
    return {"status": "healthy", "service": settings.PROJECT_NAME}
