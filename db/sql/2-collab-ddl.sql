-- **********************************
-- ***** Tables Collaboration *******
-- **********************************

-- Table teams
CREATE TABLE teams (
    code             VARCHAR(50)  NOT NULL,
    name             VARCHAR(100) NOT NULL,
    description      VARCHAR(500),
    lead             BIGINT,
    chat_channel_url VARCHAR(500),
    kanban_board_url VARCHAR(500),
    is_active        BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ,
    CONSTRAINT pk_teams PRIMARY KEY (code)
);

-- Table assignments
CREATE TABLE assignments (
    id           BIGINT GENERATED ALWAYS AS IDENTITY,
    team         VARCHAR(50),
    user_id      BIGINT       NOT NULL,
    role         VARCHAR(50)  NOT NULL,
    observation  VARCHAR(500),
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
    repo_url    VARCHAR(500),
    status      VARCHAR(100)  NOT NULL, -- references List_items where list='PROJECT_STATUS'
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
    scale       VARCHAR(100),
    unit        VARCHAR(100), -- references List_items where list='DIMENSIONS_UNIT'
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
    value        VARCHAR(100) NOT NULL, -- references List_items where list IN ['GENAI_DEV_ADOPTION', 'GENAI_QA_ADOPTION', ...]
    observation  VARCHAR(500),
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
INSERT INTO lists (code, name, description, type, module, is_active) VALUES (
    'PROJECT_STATUS', 'Project status values',
    'List of possible status values for Projects in SynapxIA (planned, in progress, on hold or complete).',
    'LIST_OF_VALUES', 'COLLAB', TRUE);
INSERT INTO list_items (list, value, label, sort_order, is_active) VALUES
    ('PROJECT_STATUS', 'PLANNED', 'Planned',   10, TRUE),
    ('PROJECT_STATUS', 'IN_PROGRESS', 'In Progress', 20, TRUE),
    ('PROJECT_STATUS', 'ON_HOLD', 'On Hold',  30, TRUE),
    ('PROJECT_STATUS', 'COMPLETED','Completed', 40, TRUE);

-- ===== List: Dimensions Unit =====
INSERT INTO lists (code, name, description, type, module, is_active) VALUES (
    'DIMENSIONS_UNIT', 'Dimensions unit values',
    'List of possible unit values for Dimensions in SynapxIA (e.g., hours, days, etc.).',
    'LIST_OF_VALUES', 'COLLAB', TRUE);
INSERT INTO list_items (list, value, label, sort_order, is_active) VALUES
    ('DIMENSIONS_UNIT', 'PCT', 'Percentage', 10, TRUE),
    ('DIMENSIONS_UNIT', 'UNITS', 'Units', 20, TRUE),
    ('DIMENSIONS_UNIT', 'COUNT', 'Count', 30, TRUE),
    ('DIMENSIONS_UNIT', 'HOURS', 'Hours', 40, TRUE),
    ('DIMENSIONS_UNIT', 'DAYS', 'Days', 50, TRUE);

-- ===== List: GenAI Adoption for Devs =====
INSERT INTO lists (code, name, description, type, module, is_active) VALUES (
    'GENAI_DEV_ADOPTION', 'GenAI Adoption for Devs',
    'Defines levels of adoption of Generative AI tools and practices among development teams.',
    'SCALE', 'COLLAB', TRUE);
INSERT INTO list_items (list, value, label, sort_order, is_active) VALUES
    ('GENAI_DEV_ADOPTION', 'NO_USAGE',  'Github Copilot, Cursor, Windsurf or Antigravity not configured', 10, TRUE),
    ('GENAI_DEV_ADOPTION', 'LOW',       'Chat used in query mode for small scripts and code suggestions', 20, TRUE),
    ('GENAI_DEV_ADOPTION', 'MODERATE',  'Agent mode for basic generation, refactoring and bug fixing', 30, TRUE),
    ('GENAI_DEV_ADOPTION', 'HIGH',      'Custom agents and MCP for advanced generation and interaction with Azure DevOps', 40, TRUE),
    ('GENAI_DEV_ADOPTION', 'VERY_HIGH', 'Agents, multi-agents and advanced MCP for more autonomous development', 50, TRUE);
--    ('GENAI_DEV_ADOPTION', 'NO_USAGE',  'Github Copilot, Cursor, Windsurf or Antigravity not configured', 10, TRUE), RED
--    ('GENAI_DEV_ADOPTION', 'LOW',       'Chat in query mode for small scripts and code suggestions', 20, TRUE), ORANGE
--    ('GENAI_DEV_ADOPTION', 'MODERATE',  'Agent mode for basic generation, refactoring and bug fixing', 30, TRUE), YELLOW
--    ('GENAI_DEV_ADOPTION', 'HIGH',      'Custom agents and MCP for advanced generation and interaction with Azure DevOps', 40, TRUE), GREEN
--    ('GENAI_DEV_ADOPTION', 'VERY_HIGH', 'Agents, multi-agents and advanced MCP for autonomous development', 50, TRUE); BLUE

-- ===== List: GenAI Adoption for QA =====
INSERT INTO lists (code, name, description, type, module, is_active) VALUES (
    'GENAI_QA_ADOPTION', 'GenAI Adoption for QA',
    'Defines levels of adoption of Generative AI tools and practices among QA teams.',
    'SCALE', 'COLLAB', TRUE);
INSERT INTO list_items (list, value, label, sort_order, is_active) VALUES
    ('GENAI_QA_ADOPTION', 'NO_USAGE',  'Github Copilot, Cursor, Windsurf or Antigravity not configured', 10, TRUE),
    ('GENAI_QA_ADOPTION', 'LOW',       'Chat used in query mode for small scripts and code suggestions', 20, TRUE),
    ('GENAI_QA_ADOPTION', 'MODERATE',  'Agent mode for basic generation, refactoring and bug fixing', 30, TRUE),
    ('GENAI_QA_ADOPTION', 'HIGH',      'Custom agents and MCP for advanced generation and interaction with Azure DevOps', 40, TRUE),
    ('GENAI_QA_ADOPTION', 'VERY_HIGH', 'Agents, multi-agents and advanced MCP for more autonomous development', 50, TRUE);
--    ('GENAI_QA_ADOPTION', 'NO_USAGE',  'No AI tools configured for testing', 10, TRUE),
--    ('GENAI_QA_ADOPTION', 'LOW',       'Chat in query mode for small scripts and test suggestions', 20, TRUE),
--    ('GENAI_QA_ADOPTION', 'MODERATE',  'Agent mode for basic test generation and issue review', 30, TRUE),
--    ('GENAI_QA_ADOPTION', 'HIGH',      'Custom agents and MCP for testing and interaction with Azure DevOps', 40, TRUE),
--    ('GENAI_QA_ADOPTION', 'VERY_HIGH', 'Agents, multi-agents and advanced MCP for autonomous testing', 50, TRUE);
