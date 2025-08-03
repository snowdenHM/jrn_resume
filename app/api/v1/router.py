from fastapi import APIRouter

from app.api.v1.endpoints import resumes, templates, export, ats_analysis

# Create main API router
api_router = APIRouter()

# Include endpoint routers
api_router.include_router(
    resumes.router,
    prefix="/resumes",
    tags=["resumes"]
)

api_router.include_router(
    templates.router,
    prefix="/templates",
    tags=["templates"]
)

api_router.include_router(
    export.router,
    prefix="/export",
    tags=["export"]
)

api_router.include_router(
    ats_analysis.router,
    prefix="/ats",
    tags=["ats-analysis"]
)