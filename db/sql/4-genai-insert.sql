-- **********************************
-- ******* Table categories *********
-- **********************************

INSERT INTO categories (code, name, description, parent) VALUES
    ('AI_ASSETS', 'AI Assets', 'Category for all AI-related assets', NULL),
    -- Classic AI and Machine Learning Models
    ('CLASSIC_AI', 'Classic AI', 'Category for Classic AI assets', 'AI_ASSETS'),
    ('ML_MODELS', 'Machine Learning Models', 'Category for Machine Learning Models', 'CLASSIC_AI'),
    ('ALGORITHMS', 'Algorithms', 'Category for Algorithms', 'CLASSIC_AI'),
    ('DATASETS', 'Datasets', 'Category for Datasets', 'CLASSIC_AI'),
    -- Generative AI
    ('GEN_AI', 'Generative AI', 'Category for Generative AI assets', 'AI_ASSETS'),
    ('PROMPTS', 'Prompt', 'Category for Prompt', 'GEN_AI'),
    ('MCPS', 'Model Context Protocol', 'Category for MCPs servers and clients definitions', 'GEN_AI'),
    ('AGENTS', 'Agents', 'Category for AI Agents', 'GEN_AI'),
    ('AI_FLOWS', 'AI Flows', 'Category for Generative AI Flows in N8n', 'GEN_AI'),
    ('ASSISTANTS', 'Assistants aka GPTs', 'Category for AI Assistants in ChatGPT', 'GEN_AI');

-- **********************************
-- ******* Table assets *************
-- **********************************

INSERT INTO assets (id, name, reference, description, type, category, status, visibility, tags) VALUES
    (1, 'Python Web Development Incremental Prompt', 'python-web-increment.prompt.md',
    'A prompt designed to guide AI in incrementally developing web applications using Python.',
    'RESOURCE','PROMPTS', 'IN_USE', 'PUBLIC', '["python", "web", "development"]'),
    (2, 'Python Web Developer Agent', 'python-web-dev.agent.md',
    'An AI agent specialized in developing web applications using Python frameworks.',
    'RESOURCE','AGENTS', 'IN_USE', 'PUBLIC', '["python", "web", "agent"]');

-- **********************************
-- ******* Table features ****
-- **********************************

INSERT INTO features (code, name, type, description) VALUES
    -- Features that are useful for any digital asset
    ('PLATFORM', 'Digital asset platform', 'TECHNICAL',
    'Platform for the execution, deployment or storage of the digital asset.'),
    ('REPOSITORY', 'Asset repository', 'TECHNICAL',
    'The repository where the digital asset is hosted.'),
    ('LANGUAGE', 'Programming language', 'TECHNICAL',
    'The programming language used in the digital asset.'),
    ('FRAMEWORK', 'Web framework', 'TECHNICAL',
    'The web framework used in the digital asset.'),
    ('COMPLEXITY', 'Complexity level', 'GENERAL',
    'The complexity level of the digital asset.'),

    -- Features for Gen AI digital assets
    ('SUGGESTED_MODEL', 'Suggested model', 'TECHNICAL',
    'The AI model recommended for optimal performance of the digital asset.'),
    ('PROMPT_TEMPLATE', 'Prompt template', 'TECHNICAL',
    'The template structure used in the prompt to guide AI responses.'),
    ('EXAMPLE_OUTPUT', 'Example output', 'USABILITY',
    'Example output of the digital asset.');

-- **********************************
-- ***** Table characterizations ****
-- **********************************

INSERT INTO characterizations (asset, feature, value, detail) VALUES
    -- Features for Python Web Development Incremental Prompt
    (1, 'PLATFORM', 'VSCode', 'The development environment used for creating web applications.'),
    (1, 'REPOSITORY', 'Github', 'https://github.com/juanbdo/prompt-engineering-lab/tree/main/ai-web-dev-incremental'),
    (1, 'SUGGESTED_MODEL', 'GPT-4o', 'The AI model recommended for generating web application code.'),
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
$$),
    -- Features for Python Web Developer Agent
    (2, 'PLATFORM', 'VSCode', 'The platform where the AI agent operates.'),
    (2, 'REPOSITORY', 'Github', 'https://github.com/juanbdo/prompt-engineering-lab/tree/main/ai-web-dev-agent'),
    (2, 'SUGGESTED_MODEL', 'GPT-4o', 'The AI model recommended for generating web application code.'),
    (2, 'EXAMPLE_OUTPUT', 'An example of a simple web page generated using the prompt.', '<html>...</html>'),
    (2, 'PROMPT_TEMPLATE', 'Incremental Development Template',
$$---
description: 'Este agente customizado está diseñado para permitir al Desarrollador Python generar el backend y el frontend de una aplicación web utilizando una arquitectura de microservicios.'
name: python-web-dev
model: GPT-4o
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
