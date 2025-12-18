-- **********************************
-- ***** Tables Collaboration *******
-- **********************************

-- Table teams
CREATE TABLE teams (
    code             VARCHAR(50)  NOT NULL,
    name             VARCHAR(100) NOT NULL,
    description      VARCHAR(255),
    lead             BIGINT,
    chat_channel_url VARCHAR(255),
    kanban_board_url VARCHAR(255),
    is_active        BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ,
    CONSTRAINT pk_teams PRIMARY KEY (code)
);

-- Tabla assignments
CREATE TABLE assignments (
    id           BIGINT GENERATED ALWAYS AS IDENTITY,
    team         VARCHAR(50),
    user_id      BIGINT       NOT NULL,
    role         VARCHAR(50),
    observation  VARCHAR(255),
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
    description VARCHAR(255),
    team        VARCHAR(50),
    repo_url    VARCHAR(255),
    status      VARCHAR(50)  NOT NULL,
    start_date  DATE,
    end_date    DATE,
    is_active   BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ,
    CONSTRAINT pk_projects PRIMARY KEY (code)
);

-- Table dimensions
CREATE TABLE dimensions (
    code        VARCHAR(50)  NOT NULL,
    name        VARCHAR(100) NOT NULL,
    description VARCHAR(255),
    scale       VARCHAR(50)  NOT NULL,
    unit        VARCHAR(50),
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
    value        VARCHAR(100) NOT NULL,
    observation  VARCHAR(255),
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

-- Garantizar solo una asignación vigente por (team, user_id)
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
