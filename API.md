# SinapxIA API - Documentación

## Descripción

API REST construida con FastAPI para gestionar roles en una base de datos PostgreSQL. Incluye CRUD completo y se ejecuta en Docker.

## Requisitos

- Docker y Docker Compose
- O Python 3.11+ con PostgreSQL (para desarrollo local)

## Inicio Rápido con Docker

### 1. Construir y ejecutar los contenedores

```bash
docker-compose up --build
```

Esto levantará:
- **PostgreSQL** en el puerto 5433 del host (el contenedor escucha en 5432)
- **FastAPI** en puerto 8001

### 2. Acceder a la API

- **API Root**: http://localhost:8001
- **Documentación Swagger**: http://localhost:8001/docs
- **Documentación ReDoc**: http://localhost:8001/redoc
- **Health Check**: http://localhost:8001/health

## Endpoints

### Health Check
```http
GET /health
```
Verifica la conexión con la base de datos.

### Crear un Rol
```http
POST /api/roles
Content-Type: application/json

{
  "nombre": "Administrador",
  "descripcion": "Usuario administrador del sistema",
  "inicio": "2025-01-01"
}
```

**Respuesta (201):**
```json
{
  "codigo": 1,
  "nombre": "Administrador",
  "descripcion": "Usuario administrador del sistema",
  "inicio": "2025-01-01"
}
```

### Obtener Todos los Roles
```http
GET /api/roles?skip=0&limit=100
```

**Respuesta (200):**
```json
[
  {
    "codigo": 1,
    "nombre": "Administrador",
    "descripcion": "Usuario administrador del sistema",
    "inicio": "2025-01-01"
  },
  {
    "codigo": 2,
    "nombre": "Usuario",
    "descripcion": "Usuario normal del sistema",
    "inicio": "2025-01-01"
  }
]
```

### Obtener un Rol por ID
```http
GET /api/roles/1
```

**Respuesta (200):**
```json
{
  "codigo": 1,
  "nombre": "Administrador",
  "descripcion": "Usuario administrador del sistema",
  "inicio": "2025-01-01"
}
```

### Actualizar un Rol
```http
PUT /api/roles/1
Content-Type: application/json

{
  "nombre": "Admin Actualizado",
  "descripcion": "Descripción actualizada"
}
```

**Respuesta (200):**
```json
{
  "codigo": 1,
  "nombre": "Admin Actualizado",
  "descripcion": "Descripción actualizada",
  "inicio": "2025-01-01"
}
```

### Eliminar un Rol
```http
DELETE /api/roles/1
```

**Respuesta (204):** Sin contenido

## Desarrollo Local (sin Docker)

### 1. Instalar dependencias

```bash
pip install -r api/requirements.txt
```

### 2. Configurar base de datos

```bash
# Asegúrate que PostgreSQL está corriendo
psql -U postgres -f bd/roles.sql
```

### 3. Ejecutar la API

```bash
cd api
uvicorn main:app --reload
```

## Estructura del Proyecto

```
sinapxia/
├── api/
│   ├── main.py              # Aplicación FastAPI con CRUD
│   └── requirements.txt      # Dependencias Python
├── bd/
│   └── roles.sql            # Esquema de base de datos
├── Dockerfile               # Imagen Docker de la API
├── docker-compose.yml       # Configuración de contenedores
├── .env                     # Variables de entorno
└── API.md                   # Esta documentación
```

## Variables de Entorno

Configurables en `.env`:

```
DB_HOST=db              # Host de PostgreSQL
DB_NAME=sinapxia        # Nombre de la base de datos
DB_USER=postgres        # Usuario de PostgreSQL
DB_PASSWORD=postgres    # Contraseña de PostgreSQL
DB_PORT=5432            # Puerto interno del contenedor (API + PgAdmin usan db:5432)
DB_HOST_PORT=5433       # Puerto publicado en el host (localhost:5433) para evitar choques con un 5432 local
```

## Comandos Útiles

### Iniciar los contenedores
```bash
docker-compose up
```

### Parar los contenedores
```bash
docker-compose down
```

### Eliminar volúmenes (limpia la base de datos)
```bash
docker-compose down -v
```

### Ver logs de la API
```bash
docker-compose logs -f api
```

### Ver logs de la base de datos
```bash
docker-compose logs -f db
```

### Acceder a PostgreSQL dentro del contenedor
```bash
docker-compose exec db psql -U postgres -d sinapxia
```

## Códigos de Respuesta HTTP

| Código | Descripción |
|--------|-------------|
| 200 | OK - Operación exitosa |
| 201 | Created - Recurso creado |
| 204 | No Content - Operación exitosa sin contenido |
| 400 | Bad Request - Solicitud inválida |
| 404 | Not Found - Recurso no encontrado |
| 500 | Internal Server Error - Error del servidor |
| 503 | Service Unavailable - Base de datos no disponible |

## Testing

Puedes probar la API usando:

- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc
- **cURL**:

```bash
# Crear rol
curl -X POST http://localhost:8001/api/roles \
  -H "Content-Type: application/json" \
  -d '{"nombre": "Rol Test", "descripcion": "Descripción"}'

# Obtener todos los roles
curl http://localhost:8001/api/roles

# Obtener rol específico
curl http://localhost:8001/api/roles/1

# Actualizar rol
curl -X PUT http://localhost:8001/api/roles/1 \
  -H "Content-Type: application/json" \
  -d '{"nombre": "Rol Actualizado"}'

# Eliminar rol
curl -X DELETE http://localhost:8001/api/roles/1
```

## Notas

- La API conecta automáticamente con PostgreSQL usando las credenciales en `.env`
- Los datos persisten en el volumen `postgres_data`
- La tabla `roles` se crea automáticamente al iniciar el contenedor
- CORS está habilitado para todas las solicitudes
