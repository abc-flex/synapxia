-- **********************************
-- ********* Table: Options *********
-- **********************************

-- ===== Module: ADMIN =====
INSERT INTO options (module, code, name, description, sort_order, type, path) VALUES
    ('ADMIN','BUSINESS_UNITS','Business Units',
     'Configuration area to define and maintain the types of organizational business units (e.g., Department, Business Unit, Chapter).',
     10,'FORM','/admin/business_units'),
    ('ADMIN','ROLES','Roles',
     'Define roles, responsibilities and access to modules and options.',
     20,'FORM','/admin/roles'),
    ('ADMIN','USERS','Users',
     'Register, update and deactivate users and associate them with roles.',
     30,'FORM','/admin/users'),
    ('ADMIN','LISTS','Lists',
     'Manage configurable lists and catalogs used throughout the platform.',
     40,'FORM','/admin/lists'),
    ('ADMIN','MODULES','Modules',
     'Register and control visibility and order of platform modules.',
     50,'FORM','/admin/modules'),
    ('ADMIN','OPTIONS','Options',
     'Configure options within each module and their visibility.',
     60,'FORM','/admin/options');

-- ===== Module: CATALOG =====
INSERT INTO options (module, code, name, description, sort_order, type, path) VALUES
    ('CATALOG','CATEGORIES','Categories',
     'Define and maintain the taxonomy of digital asset categories.',
     10,'FORM','/catalog/categories'),
    ('CATALOG','CHARACTERISTICS','Characteristics',
     'Define metadata and attributes describing digital assets.',
     20,'FORM','/catalog/characteristics'),
    ('CATALOG','ASSETS','Assets',
     'Inventory of digital assets linked to owners, initiatives and processes.',
     30,'FORM','/catalog/assets');

-- ===== Module: COLLAB =====
INSERT INTO options (module, code, name, description, sort_order, type, path) VALUES
    ('COLLAB','TEAMS','Teams',
     'Create and maintain cross-functional teams.',
     10,'FORM','/collab/teams'),
    ('COLLAB','PROJECTS','Projects',
     'Register and follow AI-related projects or workstreams.',
     20,'FORM','/collab/projects'),
    ('COLLAB','DIMENSIONS','Dimensions',
     'Define dimensions for segmentation and analysis.',
     30,'FORM','/collab/dimensions'),
    ('COLLAB','DASHBOARD','Dashboard',
     'Dashboard to monitor tasks and collaboration workload.',
     40,'FORM','/collab/dashboard');

-- ===== Module: GEN_AI =====
INSERT INTO options (module, code, name, description, sort_order, type, path) VALUES
    ('GEN_AI','PROMPTS','Prompts',
     'Curated gallery of reusable GenAI prompts.',
     10,'FORM','/genai/prompts'),
    ('GEN_AI','MCPS','MCPs',
     'Repository of tools compatible with Model Context Protocol.',
     20,'FORM','/genai/mcps'),
    ('GEN_AI','RAG_APPS','RAG Apps',
     'Configure and monitor RAG use cases.',
     30,'FORM','/genai/rag_apps'),
    ('GEN_AI','MODELS','Models',
     'Catalog of AI and ML models used in the platform.',
     40,'FORM','/genai/models'),
    ('GEN_AI','ASSISTANTS','Assistants',
     'Define assistants scope, tone and tools.',
     50,'FORM','/genai/assistants'),
    ('GEN_AI','AGENTS','Agents',
     'Design and govern AI agents with higher autonomy.',
     60,'FORM','/genai/agents');

-- ===== Module: INITS =====
INSERT INTO options (module, code, name, description, sort_order, type, path) VALUES
    ('INITS','PROPOSAL','Proposal',
     'Capture new GenAI initiative proposals.',
     10,'FORM','/inits/prompts'),
    ('INITS','EXPLORE','Explore',
     'Browse and analyze the initiative portfolio.',
     20,'FORM','/inits/explore'),
    ('INITS','PROMOTE','Promote',
     'Convert mature initiatives into reusable assets.',
     30,'FORM','/inits/promote');

-- ===== Module: INSIGHTS =====
INSERT INTO options (module, code, name, description, sort_order, type, path) VALUES
    ('INSIGHTS','KPIS','KPIs',
     'Define and track performance indicators.',
     10,'FORM','/insights/kpis'),
    ('INSIGHTS','DASHBOARDS','Dashboards',
     'Dashboards for adoption and impact analysis.',
     20,'FORM','/insights/dashboards'),
    ('INSIGHTS','REPORTS','Reports',
     'Scheduled and on-demand GenAI reports.',
     30,'FORM','/insights/reports');

-- ===== Module: WORKFLOWS =====
INSERT INTO options (module, code, name, description, sort_order, type, path) VALUES
    ('WORKFLOWS','VALUE_CHAIN','Value Chain',
     'Identify stages where AI can create impact.',
     10,'FORM','/workflows/value_chain'),
    ('WORKFLOWS','MAP','Process Map',
     'High-level process landscape representation.',
     20,'FORM','/workflows/process_map'),
    ('WORKFLOWS','MODELS','Process Models',
     'Document and relate detailed process models.',
     30,'FORM','/workflows/process_models'),
    ('WORKFLOWS','AI_FLOWS','AI Flows',
     'Design multi-step AI-enabled workflows.',
     40,'FORM','/workflows/ai_flows'),
    ('WORKFLOWS','N8N','n8n',
     'Document n8n-based integrations and automations.',
     50,'FORM','/workflows/n8n');

-- **********************************
-- ********** Table: Roles **********
-- **********************************

INSERT INTO roles (code, name, description, is_active)
VALUES
    ('ADMINISTRATOR',
     'Platform Administrator',
     'Full access to all modules and options in SynapxIA, including configuration, security and operational capabilities.',
     TRUE),
    ('ADMINISTRATIVE',
     'Operational Administrator',
     'Administrative role with full edit access to collaboration, Generative AI, AI initiatives, metrics, processes and digital assets, but without platform-level administration features.',
     TRUE),
    ('COLLABORATOR',
     'Standard Collaborator',
     'Operational user with read access to collaboration, Generative AI, AI initiatives, processes and digital assets, and edit rights only for AI initiative proposals.',
     TRUE);

-- **********************************
-- ******** Table: Privileges ********
-- **********************************

-- ===== Role: ADMINISTRATOR =====
INSERT INTO privileges (role, module, option, can_edit)
VALUES
    -- ADMIN
    ('ADMINISTRATOR','ADMIN','UNITS',   TRUE),
    ('ADMINISTRATOR','ADMIN','ROLES',   TRUE),
    ('ADMINISTRATOR','ADMIN','USERS',   TRUE),
    ('ADMINISTRATOR','ADMIN','LISTS',   TRUE),
    ('ADMINISTRATOR','ADMIN','MODULES', TRUE),
    ('ADMINISTRATOR','ADMIN','OPTIONS', TRUE),

    -- COLLAB
    ('ADMINISTRATOR','COLLAB','TEAMS',      TRUE),
    ('ADMINISTRATOR','COLLAB','PROJECTS',   TRUE),
    ('ADMINISTRATOR','COLLAB','DIMENSIONS', TRUE),
    ('ADMINISTRATOR','COLLAB','DASHBOARD',  TRUE),

    -- GEN_AI
    ('ADMINISTRATOR','GEN_AI','PROMPTS',    TRUE),
    ('ADMINISTRATOR','GEN_AI','MCPS',       TRUE),
    ('ADMINISTRATOR','GEN_AI','RAG_APPS',   TRUE),
    ('ADMINISTRATOR','GEN_AI','MODELS',     TRUE),
    ('ADMINISTRATOR','GEN_AI','ASSISTANTS', TRUE),
    ('ADMINISTRATOR','GEN_AI','AGENTS',     TRUE),

    -- INITS
    ('ADMINISTRATOR','INITS','PROPOSAL', TRUE),
    ('ADMINISTRATOR','INITS','EXPLORE',  TRUE),
    ('ADMINISTRATOR','INITS','PROMOTE',  TRUE),

    -- CATALOG
    ('ADMINISTRATOR','CATALOG','CATEGORIES',      TRUE),
    ('ADMINISTRATOR','CATALOG','CHARACTERISTICS', TRUE),
    ('ADMINISTRATOR','CATALOG','ASSETS',          TRUE),

    -- INSIGHTS
    ('ADMINISTRATOR','INSIGHTS','KPIS',       TRUE),
    ('ADMINISTRATOR','INSIGHTS','DASHBOARDS', TRUE),
    ('ADMINISTRATOR','INSIGHTS','REPORTS',    TRUE),

    -- WORKFLOWS
    ('ADMINISTRATOR','WORKFLOWS','VALUE_CHAIN', TRUE),
    ('ADMINISTRATOR','WORKFLOWS','MAP',         TRUE),
    ('ADMINISTRATOR','WORKFLOWS','MODELS',      TRUE),
    ('ADMINISTRATOR','WORKFLOWS','AI_FLOWS',    TRUE),
    ('ADMINISTRATOR','WORKFLOWS','N8N',         TRUE);

-- ===== Role: ADMINISTRATIVE =====
INSERT INTO privileges (role, module, option, can_edit)
VALUES
    -- COLLAB
    ('ADMINISTRATIVE','COLLAB','TEAMS',      TRUE),
    ('ADMINISTRATIVE','COLLAB','PROJECTS',   TRUE),
    ('ADMINISTRATIVE','COLLAB','DIMENSIONS', TRUE),
    ('ADMINISTRATIVE','COLLAB','DASHBOARD',  TRUE),

    -- GEN_AI
    ('ADMINISTRATIVE','GEN_AI','PROMPTS',    TRUE),
    ('ADMINISTRATIVE','GEN_AI','MCPS',       TRUE),
    ('ADMINISTRATIVE','GEN_AI','RAG_APPS',   TRUE),
    ('ADMINISTRATIVE','GEN_AI','MODELS',     TRUE),
    ('ADMINISTRATIVE','GEN_AI','ASSISTANTS', TRUE),
    ('ADMINISTRATIVE','GEN_AI','AGENTS',     TRUE),

    -- INITS
    ('ADMINISTRATIVE','INITS','PROPOSAL', TRUE),
    ('ADMINISTRATIVE','INITS','EXPLORE',  TRUE),
    ('ADMINISTRATIVE','INITS','PROMOTE',  TRUE),

    -- CATALOG
    ('ADMINISTRATIVE','CATALOG','CATEGORIES',      TRUE),
    ('ADMINISTRATIVE','CATALOG','CHARACTERISTICS', TRUE),
    ('ADMINISTRATIVE','CATALOG','ASSETS',          TRUE),

    -- INSIGHTS
    ('ADMINISTRATIVE','INSIGHTS','KPIS',       TRUE),
    ('ADMINISTRATIVE','INSIGHTS','DASHBOARDS', TRUE),
    ('ADMINISTRATIVE','INSIGHTS','REPORTS',    TRUE),

    -- WORKFLOWS
    ('ADMINISTRATIVE','WORKFLOWS','VALUE_CHAIN', TRUE),
    ('ADMINISTRATIVE','WORKFLOWS','MAP',         TRUE),
    ('ADMINISTRATIVE','WORKFLOWS','MODELS',      TRUE),
    ('ADMINISTRATIVE','WORKFLOWS','AI_FLOWS',    TRUE),
    ('ADMINISTRATIVE','WORKFLOWS','N8N',         TRUE);

-- ===== Role: COLLABORATOR =====
INSERT INTO privileges (role, module, option, can_edit)
VALUES
    -- COLLAB (read-only)
    ('COLLABORATOR','COLLAB','TEAMS',      FALSE),
    ('COLLABORATOR','COLLAB','PROJECTS',   FALSE),
    ('COLLABORATOR','COLLAB','DIMENSIONS', FALSE),
    ('COLLABORATOR','COLLAB','DASHBOARD',  FALSE),

    -- GEN_AI (read-only)
    ('COLLABORATOR','GEN_AI','PROMPTS',    FALSE),
    ('COLLABORATOR','GEN_AI','MCPS',       FALSE),
    ('COLLABORATOR','GEN_AI','RAG_APPS',   FALSE),
    ('COLLABORATOR','GEN_AI','MODELS',     FALSE),
    ('COLLABORATOR','GEN_AI','ASSISTANTS', FALSE),
    ('COLLABORATOR','GEN_AI','AGENTS',     FALSE),

    -- INITS
    ('COLLABORATOR','INITS','PROPOSAL', TRUE),
    ('COLLABORATOR','INITS','EXPLORE',  FALSE),
    ('COLLABORATOR','INITS','PROMOTE',  FALSE),

    -- CATALOG (read-only)
    ('COLLABORATOR','CATALOG','CATEGORIES',      FALSE),
    ('COLLABORATOR','CATALOG','CHARACTERISTICS', FALSE),
    ('COLLABORATOR','CATALOG','ASSETS',          FALSE),

    -- WORKFLOWS (read-only)
    ('COLLABORATOR','WORKFLOWS','VALUE_CHAIN', FALSE),
    ('COLLABORATOR','WORKFLOWS','MAP',         FALSE),
    ('COLLABORATOR','WORKFLOWS','MODELS',      FALSE),
    ('COLLABORATOR','WORKFLOWS','AI_FLOWS',    FALSE),
    ('COLLABORATOR','WORKFLOWS','N8N',         FALSE);

-- **********************************
-- ********** Table Units ***********
-- **********************************

INSERT INTO business_units (code, name, description, type, parent, is_active) VALUES
    ('CORP', 'Corporate', 'Corporate Unit', 'BUSINESS_UNIT', NULL, TRUE),
    ('ENG', 'Engineering', 'Engineering Department', 'DEPARTMENT', 'CORP', TRUE),
    ('GEN_AI', 'Generative AI', 'Generative AI', 'CHAPTER', 'ENG', TRUE);

-- **********************************
-- ********** Table Users ***********
-- **********************************

INSERT INTO users (id, username, email, password_hash, first_name, last_name, menu_role, business_unit, is_active) VALUES
   (0,
    'admin',
    'admin@synapxia.org',
    'SCRAM-SHA-256$4096:erZkGksCVwc49r8o18VeSg==$2c7cw07foNs0h+cLgJYdpcc7da/tjQRH7v5Y8UP0ugo=:yw24DEvmi0xGcE7qj2Y7g+QwCxuoO4q6JhZsaLkzMlg=',
    -- Password: Admin123*
    'Platform',
    'Administrator',
    'ADMINISTRATOR',
    'GEN_AI',
    TRUE);
