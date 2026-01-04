import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .admin.routes import health as admin_health_router
from .admin.routes import roles as roles_router
from .admin.routes import modules as modules_router
from .admin.routes import lists as lists_router
from .admin.routes import list_items as list_items_router
from .admin.routes import units as units_router
from .admin.routes import users as users_router
from .admin.routes import options as options_router
from .admin.routes import privileges as privileges_router

from .catalog.routes import categories as categories_router
from .catalog.routes import characteristics as characteristics_router
from .catalog.routes import assets as assets_router
from .catalog.routes import characterizations as characterizations_router
from .catalog.routes import favorites as favorites_router
from .catalog.routes import actions as actions_router
from .catalog.routes import asset_relations as asset_relations_router

from .collab.routes import teams as teams_router
from .collab.routes import assignments as assignments_router
from .collab.routes import projects as projects_router
from .collab.routes import dimensions as dimensions_router
from .collab.routes import metrics as metrics_router

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
        {
            "name": "units",
            "description": "Unit management operations",
        },
        {
            "name": "users",
            "description": "User management operations",
        },
        {
            "name": "options",
            "description": "Option management operations",
        },
        {
            "name": "privileges",
            "description": "Privilege management operations",
        },
        {
            "name": "categories",
            "description": "Category management operations",
        },
        {
            "name": "characteristics",
            "description": "Characteristic management operations",
        },
        {
            "name": "assets",
            "description": "Asset management operations",
        },
        {
            "name": "characterizations",
            "description": "Characterization management operations",
        },
        {
            "name": "favorites",
            "description": "Favorite management operations",
        },
        {
            "name": "actions",
            "description": "Action management operations",
        },
        {
            "name": "asset_relations",
            "description": "Asset relation management operations",
        },
        {
            "name": "teams",
            "description": "Team management operations",
        },
        {
            "name": "assignments",
            "description": "Assignment management operations",
        },
        {
            "name": "projects",
            "description": "Project management operations",
        },
        {
            "name": "dimensions",
            "description": "Dimension management operations",
        },
        {
            "name": "metrics",
            "description": "Metric management operations",
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
# Administration module
app.include_router(admin_health_router.router)
app.include_router(roles_router.router)
app.include_router(modules_router.router)
app.include_router(lists_router.router)
app.include_router(list_items_router.router)
app.include_router(units_router.router)
app.include_router(users_router.router)
app.include_router(options_router.router)
app.include_router(privileges_router.router)

# Catalog module (Digital Assets)
app.include_router(categories_router.router)
app.include_router(characteristics_router.router)
app.include_router(assets_router.router)
app.include_router(characterizations_router.router)
app.include_router(favorites_router.router)
app.include_router(actions_router.router)
app.include_router(asset_relations_router.router)

# Collaboration module
app.include_router(teams_router.router)
app.include_router(assignments_router.router)
app.include_router(projects_router.router)
app.include_router(dimensions_router.router)
app.include_router(metrics_router.router)

# TODO: Agregar routers de otros módulos cuando estén implementados
# - genai (Generative AI)
# - inits (GenAI Initiatives)
# - insights (GenAI Insights)
# - workflows (Processes)


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
def read_root() -> dict:
    """
    Endpoint raíz de la API.
    
    Retorna información básica sobre la API y sus endpoints principales.
    """
    return {
        "message": "SynapxIA API - System for Insight, Adoption, Practice & eXpansion through Intelligent Agents",
        "version": "1.0.0",
        "endpoints": {
            "admin": {
                "roles": "/api/roles",
                "modules": "/api/modules",
                "lists": "/api/lists",
                "list_items": "/api/list_items",
                "units": "/api/units",
                "users": "/api/users",
                "options": "/api/options",
                "privileges": "/api/privileges",
            },
            "catalog": {
                "categories": "/api/categories",
                "characteristics": "/api/characteristics",
                "assets": "/api/assets",
                "characterizations": "/api/characterizations",
                "favorites": "/api/favorites",
                "actions": "/api/actions",
                "asset_relations": "/api/asset_relations",
            },
            "collab": {
                "teams": "/api/teams",
                "assignments": "/api/assignments",
                "projects": "/api/projects",
                "dimensions": "/api/dimensions",
                "metrics": "/api/metrics",
            },
            "health": "/health",
            "docs": "/docs",
            "redoc": "/redoc",
        },
    }
