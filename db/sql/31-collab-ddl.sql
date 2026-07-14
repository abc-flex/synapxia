-- **********************************
-- ***** Tables Collaboration *******
-- **********************************

-- Table teams
CREATE TABLE teams (
    code             VARCHAR(50)  NOT NULL,
    name             VARCHAR(100) NOT NULL,
    description      VARCHAR(500),
    lead             BIGINT,
    chat_channel_url TEXT,
    kanban_board_url TEXT,
    is_active        BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ,
    CONSTRAINT pk_teams PRIMARY KEY (code)
);

-- Table roles
CREATE TABLE roles (
    code        VARCHAR(50)  NOT NULL,
    name        VARCHAR(100) NOT NULL,
    description VARCHAR(500),
    icon        TEXT,
    is_active   BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ,
    CONSTRAINT pk_roles PRIMARY KEY (code)
);

-- Table assignments
CREATE TABLE assignments (
    id           BIGINT GENERATED ALWAYS AS IDENTITY,
    team         VARCHAR(50),
    user_id      BIGINT       NOT NULL,
    role         VARCHAR(50)  NOT NULL,
    observation  TEXT,
    valid_from   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    valid_to     TIMESTAMPTZ,
    is_active    BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ,
    CONSTRAINT pk_assignments PRIMARY KEY (id)
);

-- Table projects
CREATE TABLE projects (
    code        VARCHAR(50)  NOT NULL,
    name        VARCHAR(100) NOT NULL,
    description VARCHAR(500),
    team        VARCHAR(50),
    repo_url    TEXT,
    status      VARCHAR(100)  NOT NULL, -- references List_items.value where list='PROJECT_STATUS'
    start_date  DATE,
    end_date    DATE,
    detail      TEXT,
    is_active   BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ,
    CONSTRAINT pk_projects PRIMARY KEY (code)
);

-- Table dimensions
CREATE TABLE dimensions (
    code        VARCHAR(50)  NOT NULL,
    name        VARCHAR(100) NOT NULL,
    description VARCHAR(500),
    scale       VARCHAR(100), -- references Lists.code where type='SCALE'
    unit        VARCHAR(100), -- references List_items.value where list='DIMENSIONS_UNIT'
    is_active   BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ,
    CONSTRAINT pk_dimensions PRIMARY KEY (code)
);

-- Table metrics
CREATE TABLE metrics (
    id           BIGINT GENERATED ALWAYS AS IDENTITY,
    dimension    VARCHAR(50)  NOT NULL,
    assignment   BIGINT       NOT NULL,
    value        TEXT         NOT NULL, -- Any or references List_items.value where list IN [select code from lists where type='SCALE']
    observation  TEXT,
    measured_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    is_active    BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ,
    CONSTRAINT pk_metrics PRIMARY KEY (id)
);

-- ****************************************
-- ************ Foreign Keys **************
-- ****************************************

-- FK: teams.lead → users.id
ALTER TABLE teams
    ADD CONSTRAINT fk_teams_users
    FOREIGN KEY (lead)
    REFERENCES users (id);

-- FK: assignments.team → teams.code
ALTER TABLE assignments
    ADD CONSTRAINT fk_assignments_teams
    FOREIGN KEY (team)
    REFERENCES teams (code);

-- FK: assignments.user_id → users.id
ALTER TABLE assignments
    ADD CONSTRAINT fk_assignments_users
    FOREIGN KEY (user_id)
    REFERENCES users (id);

-- FK: assignments.role → roles.code
ALTER TABLE assignments
    ADD CONSTRAINT fk_assignments_roles
    FOREIGN KEY (role)
    REFERENCES roles (code);

-- Ensure only one active assignment per (team, user_id)
CREATE UNIQUE INDEX uq_assignments_team_user_active
ON assignments (team, user_id)
WHERE valid_to IS NULL;

-- projects.team → teams.code
ALTER TABLE projects
    ADD CONSTRAINT fk_projects_teams
    FOREIGN KEY (team)
    REFERENCES teams (code);

-- dimensions.scale → lists.code
ALTER TABLE dimensions
    ADD CONSTRAINT fk_dimensions_lists
    FOREIGN KEY (scale)
    REFERENCES lists (code);

-- metrics.dimension → dimensions.code
ALTER TABLE metrics
    ADD CONSTRAINT fk_metrics_dimensions
    FOREIGN KEY (dimension)
    REFERENCES dimensions (code);

-- metrics.assigment → assigments.id
ALTER TABLE metrics
    ADD CONSTRAINT fk_metrics_assignments
    FOREIGN KEY (assignment)
    REFERENCES assignments (id);

-- **********************************
-- ***** Table lists/list_items *****
-- **********************************

-- ===== List: Project Status =====
INSERT INTO lists (code, name, description, type, module) VALUES (
    'PROJECT_STATUS', 'Project status values',
    'List of possible status values for Projects in SynapxIA (planned, in progress, on hold or complete).',
    'LIST_OF_VALUES', 'COLLAB');
INSERT INTO list_items (list, lang, value, label, sort_order) VALUES
    ('PROJECT_STATUS', 'en', 'PLANNED', 'Planned',   10),
    ('PROJECT_STATUS', 'en', 'IN_PROGRESS', 'In Progress', 20),
    ('PROJECT_STATUS', 'en', 'ON_HOLD', 'On Hold',  30),
    ('PROJECT_STATUS', 'en', 'COMPLETED','Completed', 40);

-- ===== List: Dimensions Unit =====
INSERT INTO lists (code, name, description, type, module) VALUES (
    'DIMENSIONS_UNIT', 'Dimensions unit values',
    'List of possible unit values for Dimensions in SynapxIA (e.g., hours, days, etc.).',
    'LIST_OF_VALUES', 'COLLAB');
INSERT INTO list_items (list, lang, value, label, sort_order) VALUES
    ('DIMENSIONS_UNIT', 'en', 'PCT', 'Percentage', 10),
    ('DIMENSIONS_UNIT', 'en', 'UNITS', 'Units', 20),
    ('DIMENSIONS_UNIT', 'en', 'COUNT', 'Count', 30),
    ('DIMENSIONS_UNIT', 'en', 'HOURS', 'Hours', 40),
    ('DIMENSIONS_UNIT', 'en', 'DAYS', 'Days', 50);

-- ===== List: GenAI Adoption for Devs =====
INSERT INTO lists (code, name, description, type, module) VALUES (
    'GENAI_DEV_ADOPTION', 'GenAI Adoption for Devs',
    'Defines levels of adoption of Generative AI tools and practices among development teams.',
    'SCALE', 'COLLAB');
INSERT INTO list_items (list, lang, value, label, sort_order) VALUES
    ('GENAI_DEV_ADOPTION', 'en', 'NO_USAGE',  'Github Copilot, Cursor, Windsurf or Antigravity not configured', 10),
    ('GENAI_DEV_ADOPTION', 'en', 'LOW',       'Chat used in query mode for small scripts and code suggestions', 20),
    ('GENAI_DEV_ADOPTION', 'en', 'MODERATE',  'Agent mode for basic generation, refactoring and bug fixing', 30),
    ('GENAI_DEV_ADOPTION', 'en', 'HIGH',      'Custom agents and MCP for advanced generation and interaction with Azure DevOps', 40),
    ('GENAI_DEV_ADOPTION', 'en', 'VERY_HIGH', 'Agents, multi-agents and advanced MCP for more autonomous development', 50);
INSERT INTO list_items (list, lang, value, label, sort_order) VALUES
    ('GENAI_DEV_ADOPTION', 'es', 'NO_USAGE',  'No configurado Github Copilot, Cursor, Windsurf o Antigravity', 10),
    ('GENAI_DEV_ADOPTION', 'es', 'LOW',       'Chat en modo consulta para pequeños scripts y sugerencias de código', 20),
    ('GENAI_DEV_ADOPTION', 'es', 'MODERATE',  'Modo agente para generación básica, refactorización y corrección de problemas', 30),
    ('GENAI_DEV_ADOPTION', 'es', 'HIGH',      'Agentes customizados y MCP para generación avanzada e interacción con Azure DevOps', 40),
    ('GENAI_DEV_ADOPTION', 'es', 'VERY_HIGH', 'Agentes, multi-agentes y MCP avanzado para desarrollo con autonomía', 50);

-- ===== List: GenAI Adoption for QA =====
INSERT INTO lists (code, name, description, type, module) VALUES (
    'GENAI_QA_ADOPTION', 'GenAI Adoption for QA',
    'Defines levels of adoption of Generative AI tools and practices among QA teams.',
    'SCALE', 'COLLAB');
INSERT INTO list_items (list, lang, value, label, sort_order) VALUES
    ('GENAI_QA_ADOPTION', 'en', 'NO_USAGE',  'Github Copilot, Cursor, Windsurf or Antigravity not configured', 10),
    ('GENAI_QA_ADOPTION', 'en', 'LOW',       'Chat used in query mode for small scripts and code suggestions', 20),
    ('GENAI_QA_ADOPTION', 'en', 'MODERATE',  'Agent mode for basic generation, refactoring and bug fixing', 30),
    ('GENAI_QA_ADOPTION', 'en', 'HIGH',      'Custom agents and MCP for advanced generation and interaction with Azure DevOps', 40),
    ('GENAI_QA_ADOPTION', 'en', 'VERY_HIGH', 'Agents, multi-agents and advanced MCP for more autonomous development', 50);
INSERT INTO list_items (list, lang, value, label, sort_order) VALUES
    ('GENAI_QA_ADOPTION', 'es', 'NO_USAGE',  'No hay herramientas con IA configuradas para la realización de pruebas', 10),
    ('GENAI_QA_ADOPTION', 'es', 'LOW',       'Chat en modo consulta para pequeños scripts y sugerencias de pruebas', 20),
    ('GENAI_QA_ADOPTION', 'es', 'MODERATE',  'Modo agente para generación básica de pruebas y revisión de problemas', 30),
    ('GENAI_QA_ADOPTION', 'es', 'HIGH',      'Agentes customizados y MCP para realizar pruebas e interactuar con Azure DevOps', 40),
    ('GENAI_QA_ADOPTION', 'es', 'VERY_HIGH', 'Agentes, multi-agentes y MCP avanzado para pruebas autónomas', 50);
