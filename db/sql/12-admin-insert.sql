-- **********************************
-- ********* Table: Options *********
-- **********************************

-- ===== Module: ADMIN =====
INSERT INTO options (module, code, name, description, sort_order, type, path) VALUES
    ('ADMIN','BUSINESS_UNITS','Business Units',
     'Configuration area to define and maintain the types of organizational business units (e.g., Department, Business Unit, Chapter).',
     10,'FORM','/admin/business_units'),
    ('ADMIN','PROFILES','Profiles',
     'Define profiles, responsibilities and access to modules and options.',
     20,'FORM','/admin/profiles'),
    ('ADMIN','USERS','Users',
     'Register, update and deactivate users and associate them with profiles.',
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

-- ===== Module: TAXO =====
INSERT INTO options (module, code, name, description, sort_order, type, path) VALUES
    ('TAXO','CATEGORIES','Categories',
     'Define and maintain the taxonomy of digital asset categories.',
     10,'FORM','/taxo/categories'),
    ('TAXO','FEATURES','Features',
     'Define metadata and attributes describing digital assets.',
     20,'FORM','/taxo/features');

-- ===== Module: COLLAB =====
INSERT INTO options (module, code, name, description, sort_order, type, path) VALUES
    ('COLLAB','ROLES','Roles',
     'Define roles, responsibilities and access to collaboration features.',
     10,'FORM','/collab/roles'),
    ('COLLAB','TEAMS','Teams',
     'Create and maintain cross-functional teams.',
     20,'FORM','/collab/teams'),
    ('COLLAB','PROJECTS','Projects',
     'Register and follow AI-related projects or workstreams.',
     30,'FORM','/collab/projects'),
    ('COLLAB','DIMENSIONS','Dimensions',
     'Define dimensions for segmentation and analysis.',
     40,'FORM','/collab/dimensions'),
    ('COLLAB','DASHBOARD','Assignment Dashboard',
     'Dashboard to monitor tasks and collaboration workload.',
     50,'FORM','/collab/dashboard');

-- ===== Module: ASSET LIBRARY =====
INSERT INTO options (module, code, name, description, sort_order, type, path) VALUES
    ('LIB','ASSETS','Asset Repository',
     'Inventory of digital assets linked to owners, initiatives and processes.',
     10,'FORM','/lib/assets'),
    ('LIB','PROMPTS','Prompt Gallery',
     'Curated gallery of reusable GenAI prompts.',
     20,'FORM','/lib/prompts'),
    ('LIB','MCPS','MCP Directory',
     'Curated directory of tools compatible with Model Context Protocol.',
     30,'FORM','/lib/mcps'),
    ('LIB','AGENTS','Agent Index',
     'Index of AI agents with higher autonomy.',
     40,'FORM','/lib/agents'),
    ('LIB','FLOWS','Agentic Flows',
     'Registry of agentic flows with multiple agents and MCP tools.',
     50,'Form','/lib/agentic_flows'),
    ('LIB','SKILLS','Skill Catalog',
     'Curated catalog of reusable skills for AI agents.',
     60,'FORM','/lib/skills'),
    ('LIB','ASSISTANTS','Assistants',
     'Index of assistants scope, tone and tools.',
     70,'FORM','/lib/assistants'),
    ('LIB','RAG_APPS','RAG Apps',
     'Directory of Retrieval-Augmented Generation applications.',
     80,'FORM','/lib/rag_apps'),
    ('LIB','MODELS','Models',
     'Catalog of AI and ML models used in the platform.',
     90,'FORM','/lib/models');

-- ===== Module: INITIATIVES =====
INSERT INTO options (module, code, name, description, sort_order, type, path) VALUES
    ('INITS','PROPOSAL','Proposal',
     'Capture new initiative proposals.',
     10,'FORM','/inits/prompts'),
    ('INITS','EXPLORE','Explore',
     'Browse and analyze the initiative portfolio.',
     20,'FORM','/inits/explore');

-- ===== Module: ANALYTICS =====
INSERT INTO options (module, code, name, description, sort_order, type, path) VALUES
    ('ANA','BY_UNITS','Analytics by Unit',
     'Analyze AI adoption and impact by organizational units.',
     10,'FORM','/ana/by_units'),
    ('ANA','BY_TEAMS','Analytics by Team',
     'Analyze AI adoption and impact by teams.',
     20,'FORM','/ana/by_teams'),
    ('ANA','BY_ROLE','Analytics by Role',
     'Analyze AI adoption and impact by user roles.',
     30,'FORM','/ana/by_role');

-- ===== Module: PROCESSES =====
INSERT INTO options (module, code, name, description, sort_order, type, path) VALUES
    ('PROC','VALUE_CHAIN','Value Chain',
     'Identify stages where AI can create impact.',
     10,'FORM','/proc/value_chain'),
    ('PROC','MAP','Process Map',
     'High-level process landscape representation.',
     20,'FORM','/proc/process_map'),
    ('PROC','MODELS','Process Models',
     'Document and relate detailed process models.',
     30,'FORM','/proc/process_models');

-- **********************************
-- ********** Table: Roles **********
-- **********************************

INSERT INTO profiles (code, name, description, icon)
VALUES
    ('ADMINISTRATOR',
     'Platform Administrator',
     'Full access to all modules and options in SynapxIA, including configuration, security and operational capabilities.',
     'user-group'),
    ('ADMINISTRATIVE',
     'Operational Administrator',
     'Administrative role with full edit access to collaboration, Generative AI, AI initiatives, metrics, processes and digital assets, but without platform-level administration features.',
     'user-group'),
    ('COLLABORATOR',
     'Standard Collaborator',
     'Operational user with read access to collaboration, Generative AI, AI initiatives, processes and digital assets, and edit rights only for AI initiative proposals.',
     'user-group');

-- **********************************
-- ******** Table: Privileges ********
-- **********************************

-- ===== Role: ADMINISTRATOR =====
INSERT INTO privileges (profile, module, option, can_edit)
VALUES
    -- ADMIN
    ('ADMINISTRATOR','ADMIN','BUSINESS_UNITS', TRUE),
    ('ADMINISTRATOR','ADMIN','ROLES',          TRUE),
    ('ADMINISTRATOR','ADMIN','USERS',          TRUE),
    ('ADMINISTRATOR','ADMIN','LISTS',          TRUE),
    ('ADMINISTRATOR','ADMIN','MODULES',        TRUE),
    ('ADMINISTRATOR','ADMIN','OPTIONS',        TRUE),

    -- TAXO
    ('ADMINISTRATOR','TAXO','CATEGORIES', TRUE),
    ('ADMINISTRATOR','TAXO','FEATURES',   TRUE),

    -- COLLAB
    ('ADMINISTRATOR','COLLAB','TEAMS',      TRUE),
    ('ADMINISTRATOR','COLLAB','PROJECTS',   TRUE),
    ('ADMINISTRATOR','COLLAB','DIMENSIONS', TRUE),
    ('ADMINISTRATOR','COLLAB','DASHBOARD',  TRUE),

    -- LIB
    ('ADMINISTRATOR','LIB','ASSETS',     TRUE),
    ('ADMINISTRATOR','LIB','PROMPTS',    TRUE),
    ('ADMINISTRATOR','LIB','MCPS',       TRUE),
    ('ADMINISTRATOR','LIB','AGENTS',     TRUE),
    ('ADMINISTRATOR','LIB','FLOWS',      TRUE),
    ('ADMINISTRATOR','LIB','SKILLS',     TRUE),
    ('ADMINISTRATOR','LIB','ASSISTANTS', TRUE),
    ('ADMINISTRATOR','LIB','RAG_APPS',   TRUE),
    ('ADMINISTRATOR','LIB','MODELS',     TRUE),

    -- INITS
    ('ADMINISTRATOR','INITS','PROPOSAL', TRUE),
    ('ADMINISTRATOR','INITS','EXPLORE',  TRUE),

    -- ANA
    ('ADMINISTRATOR','ANA','BY_UNITS', TRUE),
    ('ADMINISTRATOR','ANA','BY_TEAMS', TRUE),
    ('ADMINISTRATOR','ANA','BY_ROLE',  TRUE),

    -- PROC
    ('ADMINISTRATOR','PROC','VALUE_CHAIN', TRUE),
    ('ADMINISTRATOR','PROC','MAP',         TRUE),
    ('ADMINISTRATOR','PROC','MODELS',      TRUE);

-- ===== Role: ADMINISTRATIVE =====
INSERT INTO privileges (profile, module, option, can_edit)
VALUES
    -- TAXO
    ('ADMINISTRATIVE','TAXO','CATEGORIES', TRUE),
    ('ADMINISTRATIVE','TAXO','FEATURES',   TRUE),

    -- COLLAB
    ('ADMINISTRATIVE','COLLAB','TEAMS',      TRUE),
    ('ADMINISTRATIVE','COLLAB','PROJECTS',   TRUE),
    ('ADMINISTRATIVE','COLLAB','DIMENSIONS', TRUE),
    ('ADMINISTRATIVE','COLLAB','DASHBOARD',  TRUE),

    -- LIB
    ('ADMINISTRATIVE','LIB','ASSETS',     TRUE),
    ('ADMINISTRATIVE','LIB','PROMPTS',    TRUE),
    ('ADMINISTRATIVE','LIB','MCPS',       TRUE),
    ('ADMINISTRATIVE','LIB','AGENTS',     TRUE),
    ('ADMINISTRATIVE','LIB','FLOWS',      TRUE),
    ('ADMINISTRATIVE','LIB','SKILLS',     TRUE),
    ('ADMINISTRATIVE','LIB','ASSISTANTS', TRUE),
    ('ADMINISTRATIVE','LIB','RAG_APPS',   TRUE),
    ('ADMINISTRATIVE','LIB','MODELS',     TRUE),

    -- INITS
    ('ADMINISTRATIVE','INITS','PROPOSAL', TRUE),
    ('ADMINISTRATIVE','INITS','EXPLORE',  TRUE),

    -- ANA
    ('ADMINISTRATIVE','ANA','BY_UNITS', TRUE),
    ('ADMINISTRATIVE','ANA','BY_TEAMS', TRUE),
    ('ADMINISTRATIVE','ANA','BY_ROLE',  TRUE),

    -- PROC
    ('ADMINISTRATIVE','PROC','VALUE_CHAIN', TRUE),
    ('ADMINISTRATIVE','PROC','MAP',         TRUE),
    ('ADMINISTRATIVE','PROC','MODELS',      TRUE);

-- ===== Role: COLLABORATOR =====
INSERT INTO privileges (profile, module, option, can_edit)
VALUES
    -- TAXO (read-only)
    ('COLLABORATOR','TAXO','CATEGORIES', FALSE),
    ('COLLABORATOR','TAXO','FEATURES',   FALSE),

    -- COLLAB (read-only)
    ('COLLABORATOR','COLLAB','TEAMS',      FALSE),
    ('COLLABORATOR','COLLAB','PROJECTS',   FALSE),
    ('COLLABORATOR','COLLAB','DIMENSIONS', FALSE),
    ('COLLABORATOR','COLLAB','DASHBOARD',  FALSE),

    -- LIB (read-only)
    ('COLLABORATOR','LIB','ASSETS',     FALSE),
    ('COLLABORATOR','LIB','PROMPTS',    FALSE),
    ('COLLABORATOR','LIB','MCPS',       FALSE),
    ('COLLABORATOR','LIB','AGENTS',     FALSE),
    ('COLLABORATOR','LIB','FLOWS',      FALSE),
    ('COLLABORATOR','LIB','SKILLS',     FALSE),
    ('COLLABORATOR','LIB','ASSISTANTS', FALSE),
    ('COLLABORATOR','LIB','RAG_APPS',   FALSE),
    ('COLLABORATOR','LIB','MODELS',     FALSE),

    -- INITS (read-only)
    ('COLLABORATOR','INITS','PROPOSAL', TRUE),
    ('COLLABORATOR','INITS','EXPLORE',  FALSE),

    -- ANA (read-only)
    ('COLLABORATOR','ANA','BY_UNITS', FALSE),
    ('COLLABORATOR','ANA','BY_TEAMS', FALSE),
    ('COLLABORATOR','ANA','BY_ROLE',  FALSE),

    -- PROC (read-only)
    ('COLLABORATOR','PROC','VALUE_CHAIN', FALSE),
    ('COLLABORATOR','PROC','MAP',         FALSE),
    ('COLLABORATOR','PROC','MODELS',      FALSE);

-- **********************************
-- ********** Table Units ***********
-- **********************************

INSERT INTO business_units (code, name, description, type, parent) VALUES
    ('CORP', 'Corporate', 'Corporate Unit', 'BUSINESS_UNIT', NULL),
    ('ENG', 'Engineering', 'Engineering Department', 'DEPARTMENT', 'CORP'),
    ('GEN_AI', 'Generative AI', 'Generative AI', 'CHAPTER', 'ENG');

-- **********************************
-- ********** Table Users ***********
-- **********************************

INSERT INTO users (id, username, email, password_hash, first_name, last_name, profile, unit, is_superuser) VALUES
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
