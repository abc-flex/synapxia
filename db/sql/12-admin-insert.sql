-- **********************************
-- ********* Table: Options *********
-- **********************************

-- Each option carries an `icon` name that must match a file at
-- ui/src/images/icons/<name>.svg (Heroicons-outline style, 24x24,
-- stroke-width 1.5, currentColor). The sidebar renderer inlines the SVG
-- next to the option label.

-- ===== Module: ADMIN =====
INSERT INTO options (module, code, name, description, sort_order, type, path, icon) VALUES
    ('ADMIN','BUSINESS_UNITS','Business Units',
     'Configuration area to define and maintain the types of organizational business units (e.g., Department, Business Unit, Chapter).',
     10,'FORM','/admin/business_units','building-office'),
    ('ADMIN','PROFILES','Profiles',
     'Define profiles, responsibilities and access to modules and options.',
     20,'FORM','/admin/profiles','identification'),
    ('ADMIN','USERS','Users',
     'Register, update and deactivate users and associate them with profiles.',
     30,'FORM','/admin/users','user-circle'),
    ('ADMIN','LISTS','Lists',
     'Manage configurable lists and catalogs used throughout the platform.',
     40,'FORM','/admin/lists','queue-list'),
    ('ADMIN','MODULES','Modules',
     'Register and control visibility and order of platform modules.',
     50,'FORM','/admin/modules','squares-2x2'),
    ('ADMIN','OPTIONS','Options',
     'Configure options within each module and their visibility.',
     60,'FORM','/admin/options','adjustments-horizontal');

-- ===== Module: TAXO =====
INSERT INTO options (module, code, name, description, sort_order, type, path, icon) VALUES
    ('TAXO','FEATURES','Features',
     'Define metadata and attributes describing digital assets.',
     10,'FORM','/taxo/features','swatch'),
    ('TAXO','CATEGORIES','Categories',
     'Define and maintain the taxonomy of digital asset categories.',
     20,'FORM','/taxo/categories','folder'),
    ('TAXO','TAXONOMY','View Taxonomy',
     'View the hierarchical structure of the digital asset taxonomy.',
     30,'FORM','/taxo/taxonomy','document-text');

-- ===== Module: COLLAB =====
INSERT INTO options (module, code, name, description, sort_order, type, path, icon) VALUES
    ('COLLAB','ROLES','Roles',
     'Define roles, responsibilities and access to collaboration features.',
     10,'FORM','/collab/roles','shield-check'),
    ('COLLAB','TEAMS','Teams',
     'Create and maintain cross-functional teams.',
     20,'FORM','/collab/teams','user-group'),
    ('COLLAB','PROJECTS','Projects',
     'Register and follow AI-related projects or workstreams.',
     30,'FORM','/collab/projects','folder-open'),
    ('COLLAB','DIMENSIONS','Dimensions',
     'Define dimensions for segmentation and analysis.',
     40,'FORM','/collab/dimensions','cube'),
    ('COLLAB','ASSIGNMENT','Assignment Dashboard',
     'Dashboard to monitor tasks and collaboration workload.',
     50,'FORM','/collab/assignment','clipboard-document-check');

-- ===== Module: ASSET LIBRARY =====
INSERT INTO options (module, code, name, description, sort_order, type, path, icon) VALUES
    ('LIB','ASSETS','Asset Repository',
     'Inventory of digital assets linked to owners, initiatives and processes.',
     10,'FORM','/lib/assets','archive-box'),
    ('LIB','PROMPTS','Prompt Gallery',
     'Curated gallery of reusable GenAI prompts.',
     20,'FORM','/lib/prompts','chat-bubble-bottom-center-text'),
    ('LIB','MCPS','MCP Directory',
     'Curated directory of tools compatible with Model Context Protocol.',
     30,'FORM','/lib/mcps','server-stack'),
    ('LIB','AGENTS','Agent Index',
     'Index of AI agents with higher autonomy.',
     40,'FORM','/lib/agents','cpu-chip'),
    ('LIB','FLOWS','Agentic Flows',
     'Registry of agentic flows with multiple agents and MCP tools.',
     50,'Form','/lib/agentic_flows','arrows-right-left'),
    ('LIB','SKILLS','Skill Catalog',
     'Curated catalog of reusable skills for AI agents.',
     60,'FORM','/lib/skills','academic-cap'),
    ('LIB','ASSISTANTS','Assistants',
     'Index of assistants scope, tone and tools.',
     70,'FORM','/lib/assistants','sparkles'),
    ('LIB','RAG_APPS','RAG Apps',
     'Directory of Retrieval-Augmented Generation applications.',
     80,'FORM','/lib/rag_apps','document-magnifying-glass'),
    ('LIB','MODELS','Models',
     'Catalog of AI and ML models used in the platform.',
     90,'FORM','/lib/models','beaker');

-- ===== Module: INITIATIVES =====
INSERT INTO options (module, code, name, description, sort_order, type, path, icon) VALUES
    ('INITS','CRITERIAS','Criterias',
     'Define criteria for evaluating initiative proposals.',
     10,'FORM','/inits/criterias','check-badge'),
    ('INITS','PROPOSE','Propose',
     'Capture new initiative proposals.',
     20,'FORM','/inits/proposals','light-bulb'),
    ('INITS','EXPLORE','Explore',
     'Browse and analyze the initiative portfolio.',
     30,'FORM','/inits/explore','compass');

-- ===== Module: ANALYTICS =====
INSERT INTO options (module, code, name, description, sort_order, type, path, icon) VALUES
    ('ANA','DASHBOARDS','Dashboard Catalog',
     'Catalog of available dashboards.',
     10,'FORM','/ana/dashboards','chart-pie'),
    ('ANA','USAGE','Usage Metrics',
     'Track and analyze the usage of dashboards.',
     20,'FORM','/ana/usage','chart-bar');

-- ===== Module: PROCESSES =====
INSERT INTO options (module, code, name, description, sort_order, type, path, icon) VALUES
    ('PROC','VALUE_CHAIN','Value Chain',
     'Identify stages where AI can create impact.',
     10,'FORM','/proc/value_chain','link'),
    ('PROC','MAP','Process Map',
     'High-level process landscape representation.',
     20,'FORM','/proc/process_map','map'),
    ('PROC','MODELS','Process Models',
     'Document and relate detailed process models.',
     30,'FORM','/proc/process_models','rectangle-group');

-- **********************************
-- ******** Table: Profiles *********
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

-- ===== Profile: ADMINISTRATOR =====
INSERT INTO privileges (profile, module, option, can_edit)
VALUES
    -- ADMIN
    ('ADMINISTRATOR','ADMIN','BUSINESS_UNITS', TRUE),
    ('ADMINISTRATOR','ADMIN','PROFILES',       TRUE),
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
    ('ADMINISTRATOR','COLLAB','ASSIGNMENT',  TRUE),

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
    ('ADMINISTRATOR','INITS','PROPOSE', TRUE),
    ('ADMINISTRATOR','INITS','EXPLORE',  TRUE),

    -- ANA
    ('ADMINISTRATOR','ANA','DASHBOARDS', TRUE),
    ('ADMINISTRATOR','ANA','USAGE',      TRUE),

    -- PROC
    ('ADMINISTRATOR','PROC','VALUE_CHAIN', TRUE),
    ('ADMINISTRATOR','PROC','MAP',         TRUE),
    ('ADMINISTRATOR','PROC','MODELS',      TRUE);

-- ===== Profile: ADMINISTRATIVE =====
INSERT INTO privileges (profile, module, option, can_edit)
VALUES
    -- TAXO
    ('ADMINISTRATIVE','TAXO','CATEGORIES', TRUE),
    ('ADMINISTRATIVE','TAXO','FEATURES',   TRUE),

    -- COLLAB
    ('ADMINISTRATIVE','COLLAB','TEAMS',      TRUE),
    ('ADMINISTRATIVE','COLLAB','PROJECTS',   TRUE),
    ('ADMINISTRATIVE','COLLAB','DIMENSIONS', TRUE),
    ('ADMINISTRATIVE','COLLAB','ASSIGNMENT',  TRUE),

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
    ('ADMINISTRATIVE','INITS','PROPOSE', TRUE),
    ('ADMINISTRATIVE','INITS','EXPLORE',  TRUE),

    -- ANA
    ('ADMINISTRATIVE','ANA','DASHBOARDS', TRUE),
    ('ADMINISTRATIVE','ANA','USAGE',      TRUE),

    -- PROC
    ('ADMINISTRATIVE','PROC','VALUE_CHAIN', TRUE),
    ('ADMINISTRATIVE','PROC','MAP',         TRUE),
    ('ADMINISTRATIVE','PROC','MODELS',      TRUE);

-- ===== Profile: COLLABORATOR =====
INSERT INTO privileges (profile, module, option, can_edit)
VALUES
    -- TAXO (read-only)
    ('COLLABORATOR','TAXO','CATEGORIES', FALSE),
    ('COLLABORATOR','TAXO','FEATURES',   FALSE),

    -- COLLAB (read-only)
    ('COLLABORATOR','COLLAB','TEAMS',      FALSE),
    ('COLLABORATOR','COLLAB','PROJECTS',   FALSE),
    ('COLLABORATOR','COLLAB','DIMENSIONS', FALSE),
    ('COLLABORATOR','COLLAB','ASSIGNMENT',  FALSE),

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
    ('COLLABORATOR','INITS','PROPOSE', TRUE),
    ('COLLABORATOR','INITS','EXPLORE',  FALSE),

    -- ANA (read-only)
    ('COLLABORATOR','ANA','DASHBOARDS', FALSE),
    ('COLLABORATOR','ANA','USAGE',      FALSE),

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
    ('GEN_AI', 'Generative AI', 'Generative AI', 'AREA', 'ENG');

-- **********************************
-- ********** Table Users ***********
-- **********************************

INSERT INTO users (id, username, email, password_hash, first_name, last_name, profile, unit, is_superuser) VALUES
   (0,
    'admin',
    'admin@synapxia.org',
    '$2b$12$Q/ZWUi06lisvmpto32xbm.5r.ynn8fDfJ1fnLEPoBQqX.BqFAL5tG',
    -- Password: Admin123! (bcrypt hash, cost=12)
    'Platform',
    'Administrator',
    'ADMINISTRATOR',
    'GEN_AI',
    TRUE);

-- Keep the identity sequence aligned with the explicit ids above.
-- The admin user is id 0 (reserved); real users start at 1, so seed the
-- sequence with is_called = false to make the next nextval() return 1
-- (setval(..., 0) would fail: 0 is below the sequence minimum of 1).
SELECT setval(pg_get_serial_sequence('users', 'id'), GREATEST((SELECT MAX(id) FROM users), 1), false);