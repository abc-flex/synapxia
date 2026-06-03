-- **********************************
-- ******* Table assets *************
-- **********************************

INSERT INTO assets (id, name, reference, description, category, status, tags) VALUES
    (1, 'Python Web Development Incremental Prompt', 'python-web-increment.prompt.md',
    'A prompt designed to guide AI in incrementally developing web applications using Python.',
    'PROMPTS', 'IN_USE', '["python", "web", "development"]'),
    (2, 'GitHub MCP Server', 'https://github.com/github/github-mcp-server/',
    'An MCP providing services of the GitHub platform, such as code search, repository management and issue tracking.',
    'MCPS', 'IN_USE', '["github","mcp.server","ai-tools", "llm-tools", "developer tools"]'),
    (3, 'Python Web Developer Agent', 'python-web-dev.agent.md',
    'An AI agent specialized in developing web applications using Python frameworks.',
    'AGENTS', 'IN_USE', '["python", "web", "agent"]');

-- **********************************
-- ***** Table characterizations ****
-- **********************************

-- ===== Features for Python Web Development Incremental Prompt =====
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

-- ===== Features for GitHub MCP Server =====
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

-- ===== Features for Python Web Developer Agent =====
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

-- **********************************
-- ****** Table related_assets ******
-- **********************************

INSERT INTO related_assets (source, target, type) VALUES
    (1, 3, 'DEPENDS_ON'),
    (2, 1, 'USED_BY'),
    (3, 1, 'USED_BY');

-- **********************************
-- ******* Table actions ************
-- **********************************

INSERT INTO actions (id, asset, user_id, type, content, parent) VALUES
    (1, 1, 0, '3-PUBLICATION', NULL, NULL),
    (2, 1, 0, '6-USAGE', NULL, NULL),
    (3, 1, 0, '6-QUESTION', 'Is it possible to create the prompt and agent for a Django framework?', NULL),
    (4, 1, 0, '6-ANSWER', 'Coming soon.', 3),
    (5, 1, 0, '6-VOTE', 'POSITIVE', NULL),
    (6, 1, 0, '6-COMMENT', 'This prompt and its related agent are great.', NULL),
    (7, 2, 0, '3-PUBLICATION', NULL, NULL),
    (8, 2, 0, '6-USAGE', NULL, NULL);

-- **********************************
-- ****** Table favorite_assets *****
-- **********************************

INSERT INTO favorite_assets (user_id, asset) VALUES
    (0, 1),
    (0, 2);

-- **********************************
-- **** Table asset_permissions *****
-- **********************************

INSERT INTO asset_permissions (asset, target_type, target_code, access_level) VALUES
    (1, 'USER', '10', 'VIEW'),
    (2, 'ROLE', 'TL', 'MANAGE'),
    (2, 'TEAM', 'CORE', 'VIEW');

