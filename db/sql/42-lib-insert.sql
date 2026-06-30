-- **********************************
-- ******* Table assets *************
-- **********************************

INSERT INTO assets (id, name, reference, description, category, status, tags) VALUES
    -- ----- PROMPTS -----
    (1, 'Python Web Development Incremental Prompt', 'python-web-increment.prompt.md',
    'A prompt designed to guide AI in incrementally developing web applications using Python.',
    'PROMPTS', 'PUBLISHED', '["python", "web", "development"]'),
    (4, 'SQL Query Optimization Prompt', 'sql-query-optimization.prompt.md',
    'A prompt that guides the AI to analyze a SQL query and propose an optimized version with indexing and rewrite suggestions.',
    'PROMPTS', 'PUBLISHED', '["sql", "database", "performance", "optimization"]'),
    (5, 'React Component Generator Prompt', 'react-component-generator.prompt.md',
    'A prompt that generates accessible, typed React components from a short functional description.',
    'PROMPTS', 'PUBLISHED', '["react", "frontend", "typescript", "components"]'),
    (6, 'Unit Test Generation Prompt', 'unit-test-generation.prompt.md',
    'A prompt that generates unit tests with edge cases and mocks for a given function or module.',
    'PROMPTS', 'PUBLISHED', '["testing", "unit-tests", "quality", "tdd"]'),
    -- ----- MCPS -----
    (2, 'GitHub MCP Server', 'https://github.com/github/github-mcp-server/',
    'An MCP providing services of the GitHub platform, such as code search, repository management and issue tracking.',
    'MCPS', 'PUBLISHED', '["github","mcp.server","ai-tools", "llm-tools", "developer tools"]'),
    (7, 'PostgreSQL MCP Server', 'https://github.com/modelcontextprotocol/servers/tree/main/src/postgres',
    'An MCP server that exposes read-only access to a PostgreSQL database, allowing AI tools to inspect schemas and run safe queries.',
    'MCPS', 'PUBLISHED', '["postgres", "database", "mcp.server", "sql", "llm-tools"]'),
    (8, 'Filesystem MCP Server', 'https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem',
    'An MCP server that provides controlled access to the local filesystem for reading, writing and searching files within allowed directories.',
    'MCPS', 'PUBLISHED', '["filesystem", "files", "mcp.server", "local", "developer tools"]'),
    (9, 'Brave Search MCP Server', 'https://github.com/modelcontextprotocol/servers/tree/main/src/brave-search',
    'An MCP server that lets AI tools run web and local searches through the Brave Search API.',
    'MCPS', 'PUBLISHED', '["search", "web", "mcp.server", "brave", "llm-tools"]'),
    -- ----- AGENTS -----
    (3, 'Python Web Developer Agent', 'python-web-dev.agent.md',
    'An AI agent specialized in developing web applications using Python frameworks.',
    'AGENTS', 'PUBLISHED', '["python", "web", "agent"]'),
    (10, 'Code Review Agent', 'code-review.agent.md',
    'An AI agent specialized in reviewing pull requests, flagging bugs, security issues and style violations, and proposing fixes.',
    'AGENTS', 'PUBLISHED', '["code-review", "quality", "security", "agent"]'),
    (11, 'Technical Documentation Writer Agent', 'doc-writer.agent.md',
    'An AI agent that produces and maintains technical documentation (READMEs, API docs, ADRs) from source code and short briefs.',
    'AGENTS', 'PUBLISHED', '["documentation", "writing", "markdown", "agent"]'),
    (12, 'Test Automation Agent', 'test-automation.agent.md',
    'An AI agent that designs and maintains automated test suites, generates test cases and wires them into the CI pipeline.',
    'AGENTS', 'PUBLISHED', '["testing", "automation", "ci", "agent"]');

SELECT setval(pg_get_serial_sequence('assets', 'id'), (SELECT MAX(id) FROM assets));

-- **********************************
-- ***** Table characterizations ****
-- **********************************

-- ===== Features for Python Web Development Incremental Prompt (PROMPTS) =====
INSERT INTO characterizations (asset, feature, value, detail) VALUES
(1, 'PLATFORM', 'VSCode', 'The development environment used for creating web applications.'),
(1, 'SUGGESTED_MODEL', 'GPT-5', 'The AI model recommended for generating web application code.'),
(1, 'SUGGESTED_TEMPERATURE', '0.2', 'The temperature setting recommended for generating web application code, where lower values result in more focused and deterministic outputs.'),
(1, 'EXAMPLE_OUTPUT', 'An example of a simple web page generated using the prompt.', '<html>...</html>'),
(1, 'PROMPT_TEMPLATE', 'Incremental Development Template',
$$---
description: 'Prompt para generar el incremento necesario tanto en el backend como en el frontend para implementar la funcionalidad descrita en una historia de usuario'
name: python-web-increment
agent: python-web-dev
model: Claude Haiku 4.5 (copilot)
tools: ['edit', 'search', 'problems', 'changes', 'fetch', 'new']
---

#  Prompt para la generación del incremento

## Pasos para la generación
1. Solicitar la historia de usuario que se va a generar, la cual se puede definir en un archivo del árbol de directorios o se puede copiar directamente en el chat.
2. Preguntar si la historia de usuario requiere validaciones o información adicional para su generación, de ser necesario incluirlas en un archivo o directamente en el chat.
3. Generar el incremento necesario para implementar la funcionalidad descrita en la historia de usuario, teniendo en cuenta la "Arquitectura de Referencia" definida en el modo de chat python-web-dev(.github/chatmodes/python-web-dev.chatmode.md), incluyendo la creación de los modelos, controladores, servicios y cualquier otra lógica necesaria.

## Consideraciones
1. Considera las entidades de dominio especificadas en el modelo del archivo "gen-arch/func-req/domain-model.png".
2. Conserva el LookAndFeel del resto de la aplicación.
3. Evita generar nuevos estilos de código.
4. Asegúrate de que el código generado siga las mejores prácticas de desarrollo en Python.
5. Asegúrate de que el código generado sea compatible con las versiones de las librerías y frameworks utilizados en el proyecto.
$$);

-- ===== Features for SQL Query Optimization Prompt (PROMPTS) =====
INSERT INTO characterizations (asset, feature, value, detail) VALUES
(4, 'PLATFORM', 'VSCode', 'The development environment used to run the prompt.'),
(4, 'SUGGESTED_MODEL', 'GPT-5', 'The AI model recommended for query analysis and rewriting.'),
(4, 'SUGGESTED_TEMPERATURE', '0.1', 'A low temperature keeps the SQL output deterministic and faithful to the original semantics.'),
(4, 'EXAMPLE_OUTPUT', 'A rewritten query with an added composite index suggestion.',
$$-- Suggested index
CREATE INDEX idx_orders_customer_created ON orders (customer_id, created_at);

-- Optimized query
SELECT o.id, o.total
FROM orders o
WHERE o.customer_id = $1
  AND o.created_at >= NOW() - INTERVAL '30 days'
ORDER BY o.created_at DESC
LIMIT 50;$$),
(4, 'PROMPT_TEMPLATE', 'Query Optimization Template',
$$---
description: 'Prompt para analizar una consulta SQL y proponer una versión optimizada con índices y reescrituras.'
name: sql-query-optimization
model: GPT-5
tools: ['search', 'problems', 'fetch']
---

# Prompt para la optimización de consultas SQL

## Pasos
1. Solicitar la consulta SQL a optimizar y, si está disponible, el plan de ejecución (EXPLAIN ANALYZE).
2. Identificar cuellos de botella: escaneos secuenciales, joins sin índice, funciones sobre columnas indexadas.
3. Proponer índices, reescrituras y particionamiento cuando aplique, preservando la semántica original.

## Consideraciones
1. No cambies el resultado lógico de la consulta.
2. Justifica cada índice propuesto con la cláusula que lo aprovecha.
3. Prefiere índices compuestos en el orden correcto de selectividad.
$$);

-- ===== Features for React Component Generator Prompt (PROMPTS) =====
INSERT INTO characterizations (asset, feature, value, detail) VALUES
(5, 'PLATFORM', 'VSCode', 'The development environment used to run the prompt.'),
(5, 'SUGGESTED_MODEL', 'GPT-5', 'The AI model recommended for generating React/TypeScript components.'),
(5, 'SUGGESTED_TEMPERATURE', '0.3', 'A slightly higher temperature gives some flexibility in naming and structure while staying coherent.'),
(5, 'EXAMPLE_OUTPUT', 'A typed, accessible button component.',
$$export interface ButtonProps {
  label: string;
  onClick: () => void;
  disabled?: boolean;
}

export function Button({ label, onClick, disabled = false }: ButtonProps) {
  return (
    <button type="button" onClick={onClick} disabled={disabled} aria-disabled={disabled}>
      {label}
    </button>
  );
}$$),
(5, 'PROMPT_TEMPLATE', 'Component Generation Template',
$$---
description: 'Prompt para generar componentes React accesibles y tipados a partir de una descripción funcional.'
name: react-component-generator
model: GPT-5
tools: ['edit', 'new', 'search']
---

# Prompt para la generación de componentes React

## Pasos
1. Solicitar la descripción funcional del componente y sus props.
2. Generar el componente en TypeScript con tipos explícitos para las props.
3. Incluir atributos de accesibilidad (aria-*) y estados controlados.

## Consideraciones
1. Usa componentes funcionales y hooks, nunca clases.
2. Mantén el LookAndFeel del resto de la aplicación.
3. No introduzcas dependencias nuevas sin justificarlo.
$$);

-- ===== Features for Unit Test Generation Prompt (PROMPTS) =====
INSERT INTO characterizations (asset, feature, value, detail) VALUES
(6, 'PLATFORM', 'VSCode', 'The development environment used to run the prompt.'),
(6, 'SUGGESTED_MODEL', 'GPT-5', 'The AI model recommended for generating thorough unit tests.'),
(6, 'SUGGESTED_TEMPERATURE', '0.2', 'A low temperature keeps the generated tests focused and deterministic.'),
(6, 'EXAMPLE_OUTPUT', 'A pytest test covering the happy path and an edge case.',
$$import pytest
from app.utils import discount

def test_discount_applies_percentage():
    assert discount(100, 0.2) == 80

def test_discount_rejects_negative_rate():
    with pytest.raises(ValueError):
        discount(100, -0.1)$$),
(6, 'PROMPT_TEMPLATE', 'Unit Test Generation Template',
$$---
description: 'Prompt para generar pruebas unitarias con casos límite y mocks para una función o módulo dado.'
name: unit-test-generation
model: GPT-5
tools: ['search', 'problems', 'edit', 'runTasks']
---

# Prompt para la generación de pruebas unitarias

## Pasos
1. Solicitar la función o módulo a probar y el framework de pruebas (pytest, jest, etc.).
2. Identificar el camino feliz, los casos límite y las rutas de error.
3. Generar pruebas legibles con aserciones claras y mocks para dependencias externas.

## Consideraciones
1. Una aserción principal por prueba; nombres descriptivos.
2. Cubre valores nulos, vacíos y fuera de rango.
3. No pruebes detalles de implementación, prueba el comportamiento observable.
$$);

-- ===== Features for GitHub MCP Server (MCPS) =====
INSERT INTO characterizations (asset, feature, value, detail) VALUES
(2, 'MODE', 'Remote', 'The mode of operation for the MCP, indicating that it is accessed remotely via API calls.'),
(2, 'OVERVIEW', 'An MCP providing services of the GitHub platform, such as code search, repository management and issue tracking.', NULL),
(2, 'TOOLS', 'List of tools provided by the MCP for interacting with GitHub services.', $$['Actions', 'Code Security', 'Context', 'Copilot', 'Dependabot', 'Discussions', 'Gists', 'Git', 'Issues', 'Labels', 'Notifications', 'Organizations', 'Projects', 'Pull Requests', 'Repositories', 'Secret Protection', 'Security Advisories', 'Stargazers' , 'Users']$$),
(2, 'CONTENT', 'The content of the MCP includes the available endpoints, their functionalities, and any relevant documentation or resources for developers to effectively utilize the MCP.',
$$# GitHub MCP Server
The GitHub MCP Server connects AI tools directly to GitHub platform. This gives AI agents, assistants, and chatbots the ability to read repositories and code files, manage issues and PRs, analyze code, and automate workflows. All through natural language interactions.
## Use Cases
- Repository Management
- Issue & PR Automation
- CI/CD & Workflow Intelligence
- Code Analysis
- Team Collaboration
$$),
(2, 'SERVER_CONFIG', 'JSON for quick installation and configuration of the MCP in AI agents or tools.',
$$
{
	"servers": {
		"io.github.github/github-mcp-server": {
			"type": "http",
			"url": "https://api.githubcopilot.com/mcp/",
			"gallery": "https://api.mcp.github.com",
			"version": "0.33.0"
		}
	},
	"inputs": []
}
$$);

-- ===== Features for PostgreSQL MCP Server (MCPS) =====
INSERT INTO characterizations (asset, feature, value, detail) VALUES
(7, 'MODE', 'Local', 'The MCP runs locally and connects to a PostgreSQL instance via a connection string.'),
(7, 'OVERVIEW', 'Read-only PostgreSQL access for AI tools: inspect schemas, list tables and run safe SELECT queries.', NULL),
(7, 'TOOLS', 'List of tools exposed by the PostgreSQL MCP server.',
$$['query', 'list_schemas', 'list_tables', 'describe_table', 'list_relations']$$),
(7, 'CONTENT', 'Capabilities and usage notes for the PostgreSQL MCP server.',
$$# PostgreSQL MCP Server
Exposes a connected PostgreSQL database to AI tools as resources and read-only query tools.
## Use Cases
- Schema exploration and documentation
- Ad-hoc read-only analytics
- Query prototyping before writing application code
## Safety
- Runs every statement inside a READ ONLY transaction.
- Never exposes write/DDL operations.
$$),
(7, 'SERVER_CONFIG', 'JSON for quick installation and configuration of the MCP in AI agents or tools.',
$$
{
    "mcpServers": {
        "postgres": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://localhost/synapxia"]
        }
    }
}
$$);

-- ===== Features for Filesystem MCP Server (MCPS) =====
INSERT INTO characterizations (asset, feature, value, detail) VALUES
(8, 'MODE', 'Local', 'The MCP runs locally with access scoped to explicitly allowed directories.'),
(8, 'OVERVIEW', 'Controlled local filesystem access for AI tools: read, write and search files within allowed directories.', NULL),
(8, 'TOOLS', 'List of tools exposed by the Filesystem MCP server.',
$$['read_file', 'write_file', 'edit_file', 'list_directory', 'search_files', 'move_file']$$),
(8, 'CONTENT', 'Capabilities and usage notes for the Filesystem MCP server.',
$$# Filesystem MCP Server
Provides AI tools with sandboxed access to the local filesystem.
## Use Cases
- Reading and editing project files
- Searching across a codebase
- Generating new files from templates
## Safety
- Access is restricted to the directories passed as arguments.
- Path traversal outside the allowed roots is rejected.
$$),
(8, 'SERVER_CONFIG', 'JSON for quick installation and configuration of the MCP in AI agents or tools.',
$$
{
    "mcpServers": {
        "filesystem": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "/workspace/synapxia"]
        }
    }
}
$$);

-- ===== Features for Brave Search MCP Server (MCPS) =====
INSERT INTO characterizations (asset, feature, value, detail) VALUES
(9, 'MODE', 'Remote', 'The MCP calls the remote Brave Search API and requires an API key.'),
(9, 'OVERVIEW', 'Web and local search for AI tools through the Brave Search API, returning ranked results with snippets.', NULL),
(9, 'TOOLS', 'List of tools exposed by the Brave Search MCP server.',
$$['brave_web_search', 'brave_local_search']$$),
(9, 'CONTENT', 'Capabilities and usage notes for the Brave Search MCP server.',
$$# Brave Search MCP Server
Gives AI tools access to web and local search results via the Brave Search API.
## Use Cases
- Grounding answers with up-to-date web results
- Finding local businesses and points of interest
- Research and fact-checking workflows
## Requirements
- A Brave Search API key set in the BRAVE_API_KEY environment variable.
$$),
(9, 'SERVER_CONFIG', 'JSON for quick installation and configuration of the MCP in AI agents or tools.',
$$
{
    "mcpServers": {
        "brave-search": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-brave-search"],
            "env": { "BRAVE_API_KEY": "<your-api-key>" }
        }
    }
}
$$);

-- ===== Features for Python Web Developer Agent (AGENTS) =====
INSERT INTO characterizations (asset, feature, value, detail) VALUES
(3, 'PLATFORM', 'VSCode', 'The platform where the AI agent operates.'),
(3, 'SUGGESTED_MODEL', 'GPT-5', 'The AI model recommended for generating web application code.'),
(3, 'SUGGESTED_TEMPERATURE', '0.2', 'The temperature setting recommended for generating web application code, where lower values result in more focused and deterministic outputs.'),
(3, 'TOOLS', 'List of tools that agent can use.', $$['search/codebase', 'usages', 'problems', 'changes', 'edit/editFiles', 'search', 'new', 'runTasks']$$),
(3, 'INSTRUCTIONS', 'Incremental Development Instructions',
$$---
description: 'Este agente customizado está diseñado para permitir al Desarrollador Python generar el backend y el frontend de una aplicación web utilizando una arquitectura de microservicios.'
name: python-web-dev
model: GPT-5
handoffs:
  - label: Desplegar aplicación web en Python
    agent: python-web-deployer
    prompt: Seguir las mejores prácticas para desplegar la aplicación web generada
    send: false
tools: ['search/codebase', 'usages', 'problems', 'changes', 'edit/editFiles', 'search', 'new', 'runTasks']
---

# Arquitectura de Referencia para la Generación de Aplicaciones Web en Plataformas Python
Los componentes definidos a continuación conforman la arquitectura de referencia para generar aplicaciones web en plataformas Python:

## Base de Datos
Para almacenar la información de las diferentes tablas se usa una base datos Postgres 16 por lo que la generación en este frente se trata de generar los scripts SQL.

## Backend
El backend usa Python con la versión 0.95.1 del framework FastAPI y necesita de la generación de varios tipos de componentes como se describe a continuación:

### Generación de componentes únicos para el backend
- "db.py": conexión a la base de datos usando la librería mysql.connector considerando todos los parámetros de conexión definidos en el montaje de los contenedores
- "main.py": para inicializar la aplicación y definir las rutas que serán utilizadas para desplegar los servicios del backend usando el servidor con uvicorn.
- ".env": archivo de configuración de los parámetros de host, esquema, usuario y clave de la base de datos.

### Generación de componentes por cada entidad de dominio
La implementación de los métodos de acceso a datos se realiza con SQLAlchemy como framework de mapeo objeto-relacional; por tanto, los métodos de acceso a datos incluyendo las tareas de lectura, creación, actualización y borrado, no es necesario escribirlas. Los componentes que se deben generar para el backend son los siguientes:

- "models/{entidad}.py": con la definición de los esquemas de cada tabla usando la función declarative_base de la librería sqlalchemy.ext.declarative de SQLAlchemy. Nota: en caso de que sean pocas entidades de dominio, estas clases se pueden generar en un único archivo llamado "shared/model.py"
- "repos/{entidad}.py": solo para sistemas con lógica de base de datos compleja (en algunos contextos es llamada lógica de negocio), sirve para escribir métodos o acceso a datos (SQL) que sean requeridos por las particularidades del sistema.
- "services/{entidad}.py": con la definición de la lógica de domino (en algunos contextos es llamada lógica de negocio), sirve para convertir las operaciones CRUD (métodos de lectura, creación, actualización y borrado) en la invocación de los respectivos métodos de las clases de los models o los services.
- "routers/{entidad}.py": para la implementación de los métodos http, convirtiendo las invocaciones get, post, put y delete en llamados a los respectivos métodos de las clases de los servicios.
- Nota: para los demás elementos del backend toma las decisiones que consideres prudentes y genera los archivos y componentes necesarios.

## Frontend
El frontend usa Python con la versión 2.3.3 del framework Flask y necesita de la generación de varios tipos de componentes en los que puedes tomar las decisiones que consideres prudentes y genera los archivos y componentes necesarios.
$$);

-- ===== Features for Code Review Agent (AGENTS) =====
INSERT INTO characterizations (asset, feature, value, detail) VALUES
(10, 'PLATFORM', 'VSCode', 'The platform where the AI agent operates.'),
(10, 'SUGGESTED_MODEL', 'GPT-5', 'The AI model recommended for reviewing code and reasoning about defects.'),
(10, 'SUGGESTED_TEMPERATURE', '0.2', 'A low temperature keeps the review focused and consistent.'),
(10, 'TOOLS', 'List of tools that the agent can use.',
$$['search/codebase', 'usages', 'problems', 'changes', 'fetch', 'runTasks']$$),
(10, 'INSTRUCTIONS', 'Code Review Instructions',
$$---
description: 'Agente customizado que revisa cambios de código, detecta defectos, problemas de seguridad y desviaciones de estilo, y propone correcciones.'
name: code-review
model: GPT-5
tools: ['search/codebase', 'usages', 'problems', 'changes', 'fetch', 'runTasks']
---

# Agente de Revisión de Código

## Objetivo
Revisar el diff de un cambio (pull request) y producir hallazgos accionables.

## Procedimiento
1. Analiza el diff y el contexto de los archivos afectados.
2. Clasifica cada hallazgo: correctness, seguridad, rendimiento o estilo.
3. Para cada hallazgo, propón una corrección concreta con el snippet sugerido.
4. Prioriza los hallazgos por severidad y evita falsos positivos.

## Consideraciones
1. No reescribas código que ya es correcto.
2. Respeta las convenciones del repositorio.
3. Señala explícitamente cuando no encuentres problemas.
$$);

-- ===== Features for Technical Documentation Writer Agent (AGENTS) =====
INSERT INTO characterizations (asset, feature, value, detail) VALUES
(11, 'PLATFORM', 'VSCode', 'The platform where the AI agent operates.'),
(11, 'SUGGESTED_MODEL', 'GPT-5', 'The AI model recommended for generating clear technical documentation.'),
(11, 'SUGGESTED_TEMPERATURE', '0.4', 'A moderate temperature helps produce natural, readable prose.'),
(11, 'TOOLS', 'List of tools that the agent can use.',
$$['search/codebase', 'fetch', 'edit/editFiles', 'new']$$),
(11, 'INSTRUCTIONS', 'Documentation Writing Instructions',
$$---
description: 'Agente customizado que genera y mantiene documentación técnica (READMEs, documentación de API, ADRs) a partir del código fuente y briefs cortos.'
name: doc-writer
model: GPT-5
tools: ['search/codebase', 'fetch', 'edit/editFiles', 'new']
---

# Agente de Redacción de Documentación Técnica

## Objetivo
Producir y mantener documentación técnica precisa y legible.

## Procedimiento
1. Solicita el objetivo del documento y la audiencia (desarrollador, operador, usuario final).
2. Analiza el código o la fuente relevante para extraer hechos verificables.
3. Genera el documento en Markdown con encabezados, ejemplos y enlaces relativos.
4. Mantén la documentación sincronizada con el código cuando este cambie.

## Consideraciones
1. No inventes APIs, parámetros o comportamientos: documenta solo lo verificable.
2. Conserva el estilo y la estructura de la documentación existente.
3. Incluye ejemplos ejecutables siempre que sea posible.
$$);

-- ===== Features for Test Automation Agent (AGENTS) =====
INSERT INTO characterizations (asset, feature, value, detail) VALUES
(12, 'PLATFORM', 'VSCode', 'The platform where the AI agent operates.'),
(12, 'SUGGESTED_MODEL', 'GPT-5', 'The AI model recommended for designing and maintaining automated test suites.'),
(12, 'SUGGESTED_TEMPERATURE', '0.2', 'A low temperature keeps the generated tests reliable and reproducible.'),
(12, 'TOOLS', 'List of tools that the agent can use.',
$$['search/codebase', 'problems', 'changes', 'edit/editFiles', 'new', 'runTasks']$$),
(12, 'INSTRUCTIONS', 'Test Automation Instructions',
$$---
description: 'Agente customizado que diseña y mantiene suites de pruebas automatizadas, genera casos de prueba y los integra en el pipeline de CI.'
name: test-automation
model: GPT-5
tools: ['search/codebase', 'problems', 'changes', 'edit/editFiles', 'new', 'runTasks']
---

# Agente de Automatización de Pruebas

## Objetivo
Diseñar, generar y mantener suites de pruebas automatizadas integradas en CI.

## Procedimiento
1. Identifica las áreas de mayor riesgo y la cobertura actual.
2. Genera pruebas unitarias, de integración y de regresión según corresponda.
3. Integra la ejecución de pruebas en el pipeline de CI y reporta cobertura.
4. Mantén las pruebas estables y rápidas, eliminando flakiness.

## Consideraciones
1. Prioriza la cobertura del comportamiento crítico de negocio.
2. Aísla las pruebas de dependencias externas mediante mocks o fixtures.
3. Falla de forma clara y accionable cuando una prueba no pasa.
$$);

-- **********************************
-- ****** Table related_assets ******
-- **********************************

INSERT INTO related_assets (source, target, type) VALUES
    (1, 3, 'DEPENDS_ON'),     -- Python web prompt depends on the Python web agent
    (2, 1, 'USED_BY'),        -- GitHub MCP is used by the Python web prompt
    (3, 1, 'USED_BY'),        -- Python web agent is used by the Python web prompt
    (4, 1, 'SIMILAR_TO'),     -- SQL prompt is similar to the Python web prompt
    (4, 7, 'DEPENDS_ON'),     -- SQL prompt pairs with the PostgreSQL MCP
    (5, 1, 'SIMILAR_TO'),     -- React prompt is similar to the Python web prompt
    (6, 5, 'RELATED_TO'),     -- unit-test prompt complements the React component prompt
    (7, 8, 'RELATED_TO'),     -- PostgreSQL and Filesystem MCPs are used together
    (8, 9, 'RELATED_TO'),     -- Filesystem and Search MCPs are used together
    (9, 2, 'SIMILAR_TO'),     -- Search MCP is similar to the GitHub MCP
    (10, 1, 'DEPENDS_ON'),    -- Code Review agent leverages the Python web prompt
    (10, 6, 'DEPENDS_ON'),    -- Code Review agent uses the unit-test prompt
    (11, 10, 'SIMILAR_TO'),   -- Doc Writer agent is similar to the Code Review agent
    (11, 8, 'DEPENDS_ON'),    -- Doc Writer agent reads source via the Filesystem MCP
    (12, 10, 'SIMILAR_TO'),   -- Test Automation agent is similar to the Code Review agent
    (12, 6, 'DEPENDS_ON');    -- Test Automation agent builds on the unit-test prompt

-- **********************************
-- ******* Table actions ************
-- **********************************

INSERT INTO actions (id, asset, user_id, type, workflow_status, content, parent) VALUES
    -- ===== Asset 1 — Python Web Development Incremental Prompt (owner 1) =====
    (1, 1, 1, 'PROPOSAL', 'FINISHED', NULL, NULL),
    (2, 1, 0, 'REVIEW', 'ASSIGNED', NULL, NULL),
    (3, 1, 0, 'REVIEW', 'NOTIFIED', NULL, NULL),
    (4, 1, 0, 'REVIEW', 'FINISHED', NULL, NULL),
    (5, 1, 1, 'PUBLICATION', 'ASSIGNED', NULL, NULL),
    (6, 1, 1, 'PUBLICATION', 'NOTIFIED', NULL, NULL),
    (7, 1, 1, 'PUBLICATION', 'FINISHED', NULL, NULL),
    (8, 1, 2, 'QUESTION', NULL, 'Is it possible to create the prompt and agent for a Django framework?', NULL),
    (9, 1, 0, 'ANSWER', NULL, 'Coming soon.', 8),
    (10, 1, 0, 'VOTE', NULL, 'POSITIVE', NULL),
    (11, 1, 0, 'COMMENT', NULL, 'This prompt and its related agent are great.', NULL),
    -- ===== Asset 4 — SQL Query Optimization Prompt (owner 1) =====
    (12, 4, 1, 'PROPOSAL',    'FINISHED', NULL, NULL),
    (13, 4, 0, 'REVIEW',      'ASSIGNED', NULL, NULL),
    (14, 4, 0, 'REVIEW',      'NOTIFIED', NULL, NULL),
    (15, 4, 0, 'REVIEW',      'FINISHED', NULL, NULL),
    (16, 4, 1, 'PUBLICATION', 'ASSIGNED', NULL, NULL),
    (17, 4, 1, 'PUBLICATION', 'NOTIFIED', NULL, NULL),
    (18, 4, 1, 'PUBLICATION', 'FINISHED', NULL, NULL),
    (19, 4, 0, 'VOTE',        NULL, 'POSITIVE', NULL),
    (20, 4, 2, 'VOTE',        NULL, 'POSITIVE', NULL),
    (21, 4, 3, 'COMMENT',     NULL, 'Saved me hours tuning slow reporting queries.', NULL),
    (22, 4, 2, 'QUESTION',    NULL, 'Does it also suggest partial indexes?', NULL),
    (23, 4, 1, 'ANSWER',      NULL, 'Yes, when a WHERE clause is highly selective it proposes a partial index.', 22),
    -- ===== Asset 5 — React Component Generator Prompt (owner 2) =====
    (24, 5, 2, 'PROPOSAL',    'FINISHED', NULL, NULL),
    (25, 5, 0, 'REVIEW',      'ASSIGNED', NULL, NULL),
    (26, 5, 0, 'REVIEW',      'NOTIFIED', NULL, NULL),
    (27, 5, 0, 'REVIEW',      'FINISHED', NULL, NULL),
    (28, 5, 2, 'PUBLICATION', 'ASSIGNED', NULL, NULL),
    (29, 5, 2, 'PUBLICATION', 'NOTIFIED', NULL, NULL),
    (30, 5, 2, 'PUBLICATION', 'FINISHED', NULL, NULL),
    (31, 5, 0, 'VOTE',        NULL, 'POSITIVE', NULL),
    (32, 5, 4, 'VOTE',        NULL, 'NEGATIVE', NULL),
    (33, 5, 1, 'COMMENT',     NULL, 'Great starting point, though I tweak the generated styles.', NULL),
    -- ===== Asset 6 — Unit Test Generation Prompt (owner 3) =====
    (34, 6, 3, 'PROPOSAL',    'FINISHED', NULL, NULL),
    (35, 6, 0, 'REVIEW',      'ASSIGNED', NULL, NULL),
    (36, 6, 0, 'REVIEW',      'NOTIFIED', NULL, NULL),
    (37, 6, 0, 'REVIEW',      'FINISHED', NULL, NULL),
    (38, 6, 3, 'PUBLICATION', 'ASSIGNED', NULL, NULL),
    (39, 6, 3, 'PUBLICATION', 'NOTIFIED', NULL, NULL),
    (40, 6, 3, 'PUBLICATION', 'FINISHED', NULL, NULL),
    (41, 6, 0, 'VOTE',        NULL, 'POSITIVE', NULL),
    (42, 6, 1, 'VOTE',        NULL, 'POSITIVE', NULL),
    (43, 6, 2, 'COMMENT',     NULL, 'The generated edge cases caught a real bug for us.', NULL),
    (44, 6, 5, 'QUESTION',    NULL, 'Can it target jest as well as pytest?', NULL),
    (45, 6, 3, 'ANSWER',      NULL, 'Yes, just state the framework when you invoke the prompt.', 44),
    -- ===== Asset 7 — PostgreSQL MCP Server (owner 1) =====
    (46, 7, 1, 'PROPOSAL',    'FINISHED', NULL, NULL),
    (47, 7, 0, 'REVIEW',      'ASSIGNED', NULL, NULL),
    (48, 7, 0, 'REVIEW',      'NOTIFIED', NULL, NULL),
    (49, 7, 0, 'REVIEW',      'FINISHED', NULL, NULL),
    (50, 7, 1, 'PUBLICATION', 'ASSIGNED', NULL, NULL),
    (51, 7, 1, 'PUBLICATION', 'NOTIFIED', NULL, NULL),
    (52, 7, 1, 'PUBLICATION', 'FINISHED', NULL, NULL),
    (53, 7, 0, 'VOTE',        NULL, 'POSITIVE', NULL),
    (54, 7, 3, 'VOTE',        NULL, 'POSITIVE', NULL),
    (55, 7, 2, 'COMMENT',     NULL, 'Connects to our Neon database without any extra setup.', NULL),
    (56, 7, 4, 'QUESTION',    NULL, 'Can I restrict it to a single schema?', NULL),
    (57, 7, 1, 'ANSWER',      NULL, 'Yes, scope it through the connection string search_path.', 56),
    -- ===== Asset 8 — Filesystem MCP Server (owner 2) =====
    (58, 8, 2, 'PROPOSAL',    'FINISHED', NULL, NULL),
    (59, 8, 0, 'REVIEW',      'ASSIGNED', NULL, NULL),
    (60, 8, 0, 'REVIEW',      'NOTIFIED', NULL, NULL),
    (61, 8, 0, 'REVIEW',      'FINISHED', NULL, NULL),
    (62, 8, 2, 'PUBLICATION', 'ASSIGNED', NULL, NULL),
    (63, 8, 2, 'PUBLICATION', 'NOTIFIED', NULL, NULL),
    (64, 8, 2, 'PUBLICATION', 'FINISHED', NULL, NULL),
    (65, 8, 0, 'VOTE',        NULL, 'POSITIVE', NULL),
    (66, 8, 5, 'COMMENT',     NULL, 'Handy for local file workflows during prototyping.', NULL),
    -- ===== Asset 9 — Brave Search MCP Server (owner 3) =====
    (67, 9, 3, 'PROPOSAL',    'FINISHED', NULL, NULL),
    (68, 9, 0, 'REVIEW',      'ASSIGNED', NULL, NULL),
    (69, 9, 0, 'REVIEW',      'NOTIFIED', NULL, NULL),
    (70, 9, 0, 'REVIEW',      'FINISHED', NULL, NULL),
    (71, 9, 3, 'PUBLICATION', 'ASSIGNED', NULL, NULL),
    (72, 9, 3, 'PUBLICATION', 'NOTIFIED', NULL, NULL),
    (73, 9, 3, 'PUBLICATION', 'FINISHED', NULL, NULL),
    (74, 9, 0, 'VOTE',        NULL, 'POSITIVE', NULL),
    (75, 9, 2, 'VOTE',        NULL, 'POSITIVE', NULL),
    (76, 9, 1, 'COMMENT',     NULL, 'Grounding answers with fresh web results works great.', NULL),
    (77, 9, 4, 'QUESTION',    NULL, 'Does it support local (map) search too?', NULL),
    (78, 9, 3, 'ANSWER',      NULL, 'Yes, via the brave_local_search tool.', 77),
    -- ===== Asset 10 — Code Review Agent (owner 1) =====
    (79, 10, 1, 'PROPOSAL',    'FINISHED', NULL, NULL),
    (80, 10, 0, 'REVIEW',      'ASSIGNED', NULL, NULL),
    (81, 10, 0, 'REVIEW',      'NOTIFIED', NULL, NULL),
    (82, 10, 0, 'REVIEW',      'FINISHED', NULL, NULL),
    (83, 10, 1, 'PUBLICATION', 'ASSIGNED', NULL, NULL),
    (84, 10, 1, 'PUBLICATION', 'NOTIFIED', NULL, NULL),
    (85, 10, 1, 'PUBLICATION', 'FINISHED', NULL, NULL),
    (86, 10, 0, 'VOTE',        NULL, 'POSITIVE', NULL),
    (87, 10, 2, 'VOTE',        NULL, 'POSITIVE', NULL),
    (88, 10, 3, 'COMMENT',     NULL, 'Catches security issues our manual reviews missed.', NULL),
    (89, 10, 4, 'QUESTION',    NULL, 'Does it review TypeScript as well as Python?', NULL),
    (90, 10, 1, 'ANSWER',      NULL, 'Yes, it is language-agnostic and adapts to the repo conventions.', 89),
    -- ===== Asset 11 — Technical Documentation Writer Agent (owner 2) =====
    (91, 11, 2, 'PROPOSAL',    'FINISHED', NULL, NULL),
    (92, 11, 0, 'REVIEW',      'ASSIGNED', NULL, NULL),
    (93, 11, 0, 'REVIEW',      'NOTIFIED', NULL, NULL),
    (94, 11, 0, 'REVIEW',      'FINISHED', NULL, NULL),
    (95, 11, 2, 'PUBLICATION', 'ASSIGNED', NULL, NULL),
    (96, 11, 2, 'PUBLICATION', 'NOTIFIED', NULL, NULL),
    (97, 11, 2, 'PUBLICATION', 'FINISHED', NULL, NULL),
    (98, 11, 0, 'VOTE',        NULL, 'POSITIVE', NULL),
    (99, 11, 5, 'VOTE',        NULL, 'POSITIVE', NULL),
    (100, 11, 1, 'COMMENT',    NULL, 'Generated a solid first draft of our README in seconds.', NULL),
    -- ===== Asset 12 — Test Automation Agent (owner 3) =====
    (101, 12, 3, 'PROPOSAL',    'FINISHED', NULL, NULL),
    (102, 12, 0, 'REVIEW',      'ASSIGNED', NULL, NULL),
    (103, 12, 0, 'REVIEW',      'NOTIFIED', NULL, NULL),
    (104, 12, 0, 'REVIEW',      'FINISHED', NULL, NULL),
    (105, 12, 3, 'PUBLICATION', 'ASSIGNED', NULL, NULL),
    (106, 12, 3, 'PUBLICATION', 'NOTIFIED', NULL, NULL),
    (107, 12, 3, 'PUBLICATION', 'FINISHED', NULL, NULL),
    (108, 12, 0, 'VOTE',        NULL, 'POSITIVE', NULL),
    (109, 12, 2, 'VOTE',        NULL, 'POSITIVE', NULL),
    (110, 12, 4, 'COMMENT',     NULL, 'Wired our test suite into CI with almost no manual work.', NULL),
    (111, 12, 5, 'QUESTION',    NULL, 'Can it report coverage thresholds?', NULL),
    (112, 12, 3, 'ANSWER',      NULL, 'Yes, it fails the pipeline below the configured threshold.', 111);

-- Keep the identity sequence aligned with the explicit ids above
SELECT setval(pg_get_serial_sequence('actions', 'id'), (SELECT MAX(id) FROM actions));

-- **********************************
-- ****** Table favorite_assets *****
-- **********************************

INSERT INTO favorite_assets (user_id, asset) VALUES
    (0, 1),
    (0, 2),
    (0, 4),
    (1, 4),
    (2, 5),
    (3, 6),
    (1, 7),
    (0, 8),
    (2, 9),
    (0, 10),
    (3, 11),
    (0, 12);

-- **********************************
-- **** Table asset_permissions *****
-- **********************************

INSERT INTO asset_permissions (asset, target_type, target_code, access_level) VALUES
    (1,  'USER',   '1',       'MANAGE'),
    (1,  'USER',   '0',       'MANAGE'),
    (2,  'ROLE',   'TL',      'MANAGE'),
    (2,  'TEAM',   'CORE',    'VIEW'),
    (4,  'USER',   '1',       'MANAGE'),
    (4,  'TEAM',   'ALPHA',   'VIEW'),
    (5,  'USER',   '2',       'MANAGE'),
    (5,  'ROLE',   'FRONT',   'VIEW'),
    (6,  'USER',   '3',       'MANAGE'),
    (6,  'ROLE',   'QA',      'VIEW'),
    (7,  'USER',   '1',       'MANAGE'),
    (7,  'UNIT',   'GEN_AI',  'VIEW'),
    (8,  'USER',   '2',       'MANAGE'),
    (8,  'TEAM',   'BRAVO',   'VIEW'),
    (9,  'USER',   '3',       'MANAGE'),
    (9,  'PUBLIC', 'ALL',     'VIEW'),
    (10, 'USER',   '1',       'MANAGE'),
    (10, 'ROLE',   'BACK',    'VIEW'),
    (11, 'USER',   '2',       'MANAGE'),
    (11, 'TEAM',   'CHARLIE', 'VIEW'),
    (12, 'USER',   '3',       'MANAGE'),
    (12, 'PUBLIC', 'ALL',     'VIEW');
