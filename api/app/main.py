import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import admin as admin_router
from .routers import roles as roles_router
from .routers import modules as modules_router
from .routers import lists as lists_router
from .routers import list_items as list_items_router

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="SynapxIA API",
    version="1.0.0",
    description="API para gestión de adopción de IA - System for Insight, Adoption, Practice & eXpansion through Intelligent Agents",
    openapi_tags=[
        {
            "name": "health",
            "description": "Health check endpoints",
        },
        {
            "name": "roles",
            "description": "Role management operations",
        },
        {
            "name": "modules",
            "description": "Module management operations",
        },
        {
            "name": "lists",
            "description": "List management operations",
        },
        {
            "name": "list_items",
            "description": "List item management operations",
        },
    ],
)

# Configurar CORS
cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins if "*" not in cors_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(roles_router.router)
app.include_router(admin_router.router)
app.include_router(modules_router.router)
app.include_router(lists_router.router)
app.include_router(list_items_router.router)


@app.on_event("startup")
async def startup_event():
    """Evento de inicio de la aplicación."""
    logger.info("SynapxIA API starting up...")
    logger.info(f"Environment: {os.getenv('APP_ENV', 'development')}")


@app.on_event("shutdown")
async def shutdown_event():
    """Evento de cierre de la aplicación."""
    logger.info("SynapxIA API shutting down...")


@app.get("/", tags=["health"])
def read_root() -> dict[str, str | dict[str, str]]:
    """
    Endpoint raíz de la API.
    
    Retorna información básica sobre la API y sus endpoints principales.
    """
    return {
        "message": "SynapxIA API - System for Insight, Adoption, Practice & eXpansion through Intelligent Agents",
        "version": "1.0.0",
        "endpoints": {
            "roles": "/api/roles",
            "modules": "/api/modules",
            "lists": "/api/lists",
            "list_items": "/api/list_items",
            "health": "/health",
            "docs": "/docs",
            "redoc": "/redoc",
        },
    }
