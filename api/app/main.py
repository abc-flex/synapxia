from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import admin as admin_router
from .routers import roles as roles_router

app = FastAPI(
    title="SynapxIA API",
    version="1.0.0",
    openapi_tags=[
        {
            "name": "health",
            "description": "Health check endpoints",
        },
        {
            "name": "roles",
            "description": "Role management operations",
        },
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(roles_router.router)
app.include_router(admin_router.router)


@app.get("/", tags=["health"])
def read_root() -> dict[str, str | dict[str, str]]:
    return {
        "message": "SynapxIA API - Role Management System",
        "version": "1.0.0",
        "endpoints": {
            "roles": "/api/roles",
            "docs": "/docs",
        },
    }
