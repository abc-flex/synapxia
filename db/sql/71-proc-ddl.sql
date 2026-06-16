-- **********************************
-- ******** Tables Processes ********
-- **********************************

-- Table processes
CREATE TABLE processes (
    code         VARCHAR(50)   NOT NULL,
    name         VARCHAR(100)  NOT NULL,
    description  VARCHAR(500),
    type         VARCHAR(100)  NOT NULL, -- references List_items.value where list='PROCESS_TYPE'
    parent       VARCHAR(50),            -- self reference to processes.code
    unit         VARCHAR(50),            -- references business_units.code
    owner        BIGINT        NOT NULL, -- references users.id
    reference    TEXT,
    status       VARCHAR(100)  NOT NULL, -- references List_items.value where list='PROCESS_STATUS'
    tags         JSONB,
    detail       TEXT,
    is_active    BOOLEAN       NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ,
    CONSTRAINT pk_processes PRIMARY KEY (code)
);

-- Table process_assets
CREATE TABLE process_assets (
    process     VARCHAR(50)   NOT NULL,
    asset       BIGINT        NOT NULL,
    rationale   TEXT,
    is_active   BOOLEAN       NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ,
    CONSTRAINT pk_process_assets PRIMARY KEY (process, asset)
);

-- Table related_processes
CREATE TABLE related_processes (
    source      VARCHAR(50)   NOT NULL,
    target      VARCHAR(50)   NOT NULL,
    type        VARCHAR(100)  NOT NULL, -- references List_items.value where list='RELATION_TYPE'
    rationale   TEXT,
    is_active   BOOLEAN       NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ,
    CONSTRAINT pk_related_processes PRIMARY KEY (source, target, type)
);

-- Table process_inits
CREATE TABLE process_inits (
    process     VARCHAR(50)   NOT NULL,
    init        BIGINT        NOT NULL,
    rationale   TEXT,
    is_active   BOOLEAN       NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ,
    CONSTRAINT pk_process_inits PRIMARY KEY (process, init)
);

-- ****************************************
-- ************ Foreign Keys **************
-- ****************************************

-- processes.parent → processes.code
ALTER TABLE processes
    ADD CONSTRAINT fk_processes_parent
    FOREIGN KEY (parent)
    REFERENCES processes (code);

-- processes.unit → business_units.code
ALTER TABLE processes
    ADD CONSTRAINT fk_processes_business_units
    FOREIGN KEY (unit)
    REFERENCES business_units (code);

-- processes.owner → users.id
ALTER TABLE processes
    ADD CONSTRAINT fk_processes_users
    FOREIGN KEY (owner)
    REFERENCES users (id);

-- process_assets.process → processes.code
ALTER TABLE process_assets
    ADD CONSTRAINT fk_process_assets_processes
    FOREIGN KEY (process)
    REFERENCES processes (code);

-- process_assets.asset → assets.id
ALTER TABLE process_assets
    ADD CONSTRAINT fk_process_assets_assets
    FOREIGN KEY (asset)
    REFERENCES assets (id);

-- related_processes.source → processes.code
ALTER TABLE related_processes
    ADD CONSTRAINT fk_related_processes_source
    FOREIGN KEY (source)
    REFERENCES processes (code);

-- related_processes.target → processes.code
ALTER TABLE related_processes
    ADD CONSTRAINT fk_related_processes_target
    FOREIGN KEY (target)
    REFERENCES processes (code);

-- process_inits.process → processes.code
ALTER TABLE process_inits
    ADD CONSTRAINT fk_process_inits_processes
    FOREIGN KEY (process)
    REFERENCES processes (code);

-- process_inits.init → initiatives.id
ALTER TABLE process_inits
    ADD CONSTRAINT fk_process_inits_initiatives
    FOREIGN KEY (init)
    REFERENCES initiatives (id);

-- **********************************
-- ***** Table lists/list_items *****
-- **********************************

-- ===== List: Process Type (Porter's value chain) =====
INSERT INTO lists (code, name, description, type, module) VALUES (
    'PROCESS_TYPE', 'List of process types for system configuration',
    'List that classifies processes as primary or support activities in Porter''s value chain.',
    'LIST_OF_VALUES', 'PROC');
INSERT INTO list_items (list, lang, value, label, sort_order) VALUES
    ('PROCESS_TYPE', 'en', 'PRIMARY', 'Primary', 10),
    ('PROCESS_TYPE', 'en', 'SUPPORT', 'Support', 20);
INSERT INTO list_items (list, lang, value, label, sort_order) VALUES
    ('PROCESS_TYPE', 'es', 'PRIMARY', 'Primario', 10),
    ('PROCESS_TYPE', 'es', 'SUPPORT', 'Apoyo',    20);

-- ===== List: Process Status =====
INSERT INTO lists (code, name, description, type, module) VALUES (
    'PROCESS_STATUS', 'List of process statuses for system configuration',
    'List that classifies the statuses of processes in SynapxIA.',
    'LIST_OF_VALUES', 'PROC');
INSERT INTO list_items (list, lang, value, label, sort_order) VALUES
    ('PROCESS_STATUS', 'en', 'DRAFT',      'Draft',      10),
    ('PROCESS_STATUS', 'en', 'REVIEW',     'Review',     20),
    ('PROCESS_STATUS', 'en', 'PUBLISHED',  'Published',  30),
    ('PROCESS_STATUS', 'en', 'DEPRECATED', 'Deprecated', 40);
INSERT INTO list_items (list, lang, value, label, sort_order) VALUES
    ('PROCESS_STATUS', 'es', 'DRAFT',      'Borrador',    10),
    ('PROCESS_STATUS', 'es', 'REVIEW',     'Revisión',    20),
    ('PROCESS_STATUS', 'es', 'PUBLISHED',  'Publicado',   30),
    ('PROCESS_STATUS', 'es', 'DEPRECATED', 'Obsoleto',    40);
