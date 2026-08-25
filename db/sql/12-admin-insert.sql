-- **********************************
-- ********* Table: Options *********
-- **********************************

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
    ('COLLAB','DASHBOARD','Assignment Dashboard',
     'Dashboard to monitor tasks and collaboration workload.',
     50,'FORM','/collab/dashboard','clipboard-document-check');

-- ===== Module: ASSET LIBRARY =====
INSERT INTO options (module, code, name, description, sort_order, type, path, icon) VALUES
    ('LIB','ASSETS','Asset Management',
     'Manage and track digital assets throughout their entire lifecycle.',
     10,'CARD_GALLERY','/lib/assets','archive-box'),
    ('LIB','EXPLORE','Explore Category',
     'Browse and explore different categories of digital assets (e.g., Prompt, MCP, Agent, Flow, Skill, Assistant, RAG App, Model).',
     15,'CARD_GALLERY','/lib/explore','magnifying-glass'),
    ('LIB','PROMPTS','Prompt Gallery',
     'Curated gallery of reusable GenAI prompts.',
     20,'CARD_GALLERY','/lib/prompts','chat-bubble-bottom-center-text'),
    ('LIB','MCPS','MCP Directory',
     'Curated directory of tools compatible with Model Context Protocol.',
     30,'CARD_GALLERY','/lib/mcps','server-stack'),
    ('LIB','AGENTS','Agent Repository',
     'Inventory of AI agents with higher autonomy.',
     40,'CARD_GALLERY','/lib/agents','cpu-chip'),
    ('LIB','FLOWS','Agentic Flows',
     'Registry of agentic flows with multiple agents and MCP tools.',
     50,'CARD_GALLERY','/lib/agentic_flows','arrows-right-left'),
    ('LIB','SKILLS','Skill Catalog',
     'Curated catalog of reusable skills for AI agents.',
     60,'CARD_GALLERY','/lib/skills','academic-cap'),
    ('LIB','ASSISTANTS','Assistants',
     'Index of assistants scope, tone and tools.',
     70,'CARD_GALLERY','/lib/assistants','sparkles'),
    ('LIB','RAG_APPS','RAG Apps',
     'Directory of Retrieval-Augmented Generation applications.',
     80,'CARD_GALLERY','/lib/rag_apps','document-magnifying-glass'),
    ('LIB','MODELS','Models',
     'Catalog of AI and ML models used in the platform.',
     90,'CARD_GALLERY','/lib/models','beaker');

-- ===== Module: INITIATIVES =====
INSERT INTO options (module, code, name, description, sort_order, type, path, icon) VALUES
    ('INITS','CRITERIAS','Criterias',
     'Define criteria for evaluating initiative proposals.',
     10,'FORM','/inits/criterias','check-badge'),
    ('INITS','INITIATIVES','Initiative Management',
     'Manage and track AI initiatives throughout their entire lifecycle.',
     20,'FORM','/inits/initiatives','light-bulb'),
    ('INITS','EXPLORE','Explore Initiatives',
     'Browse and analyze the initiative portfolio.',
     30,'FORM','/inits/explore','compass');

-- ===== Module: ANALYTICS =====
INSERT INTO options (module, code, name, description, sort_order, type, path, icon) VALUES
    ('ANA','DASHBOARDS','Dashboard Management',
     'Manage and configure dashboards.',
     10,'FORM','/ana/dashboards','archive-box'),
    ('ANA','CATALOG','Dashboard Catalog',
     'Catalog of available dashboards.',
     10,'FORM','/ana/catalog','chart-pie'),
    ('ANA','USAGE','Usage Metrics',
     'Track and analyze the usage of dashboards.',
     20,'FORM','/ana/usage','chart-bar');

-- ===== Module: PROCESSES =====
INSERT INTO options (module, code, name, description, sort_order, type, path, icon) VALUES
    ('PROC','PROCESSES','Process Management',
     'Manage and configure processes.',
     10,'FORM','/proc/processes','rectangle-group'),
    ('PROC','VALUE_CHAIN','Value Chain',
     'Identify stages where AI can create impact.',
     20,'FORM','/proc/value_chain','link'),
    ('PROC','MAP','Process Map',
     'High-level process landscape representation.',
     30,'FORM','/proc/process_map','map');

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
     'user-group'),
    ('REVIEWER',
     'Reviewer',
     'Reviews proposed library assets before publication: can run the review workflow (review/modify/publish/reject) over digital assets, characterizations and actions.',
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
    ('ADMINISTRATOR','TAXO','TAXONOMY',   TRUE),

    -- COLLAB
    ('ADMINISTRATOR','COLLAB','ROLES',      TRUE),
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
    ('ADMINISTRATOR','INITS','CRITERIAS',   TRUE),
    ('ADMINISTRATOR','INITS','INITIATIVES', TRUE),
    ('ADMINISTRATOR','INITS','EXPLORE',     TRUE),

    -- ANA
    ('ADMINISTRATOR','ANA','DASHBOARDS', TRUE),
    ('ADMINISTRATOR','ANA','CATALOG',    TRUE),
    ('ADMINISTRATOR','ANA','USAGE',      TRUE),

    -- PROC
    ('ADMINISTRATOR','PROC','PROCESSES',   TRUE),
    ('ADMINISTRATOR','PROC','VALUE_CHAIN', TRUE),
    ('ADMINISTRATOR','PROC','MAP',         TRUE);

-- ===== Profile: ADMINISTRATIVE =====
INSERT INTO privileges (profile, module, option, can_edit)
VALUES
    -- TAXO
    ('ADMINISTRATIVE','TAXO','CATEGORIES', TRUE),
    ('ADMINISTRATIVE','TAXO','FEATURES',   TRUE),
    ('ADMINISTRATIVE','TAXO','TAXONOMY',   TRUE),

    -- COLLAB
    ('ADMINISTRATIVE','COLLAB','ROLES',      TRUE),
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
    ('ADMINISTRATIVE','INITS','CRITERIAS',   TRUE),
    ('ADMINISTRATIVE','INITS','INITIATIVES', TRUE),
    ('ADMINISTRATIVE','INITS','EXPLORE',     TRUE),

    -- ANA
    ('ADMINISTRATIVE','ANA','DASHBOARDS', TRUE),
    ('ADMINISTRATIVE','ANA','CATALOG',    TRUE),
    ('ADMINISTRATIVE','ANA','USAGE',      TRUE),

    -- PROC
    ('ADMINISTRATIVE','PROC','PROCESSES',   TRUE),
    ('ADMINISTRATIVE','PROC','VALUE_CHAIN', TRUE),
    ('ADMINISTRATIVE','PROC','MAP',         TRUE);

-- ===== Profile: COLLABORATOR =====
INSERT INTO privileges (profile, module, option, can_edit)
VALUES

    -- LIB
    ('COLLABORATOR','LIB','PROMPTS',    TRUE),
    ('COLLABORATOR','LIB','MCPS',       TRUE),
    ('COLLABORATOR','LIB','AGENTS',     TRUE),
    ('COLLABORATOR','LIB','FLOWS',      TRUE),
    ('COLLABORATOR','LIB','SKILLS',     TRUE),
    ('COLLABORATOR','LIB','ASSISTANTS', TRUE),
    ('COLLABORATOR','LIB','RAG_APPS',   TRUE),
    ('COLLABORATOR','LIB','MODELS',     TRUE),

    -- Independent options (read-only)
    ('COLLABORATOR','TAXO', 'TAXONOMY',   FALSE),
    ('COLLABORATOR','INITS','EXPLORE',    FALSE),
    ('COLLABORATOR','ANA',  'CATALOG',    FALSE),
    ('COLLABORATOR','PROC', 'VALUE_CHAIN',FALSE),
    ('COLLABORATOR','PROC', 'MAP',        FALSE);

-- ===== Profile: REVIEWER =====
INSERT INTO privileges (profile, module, option, can_edit)
VALUES

    -- LIB
    ('REVIEWER','LIB','PROMPTS',    TRUE),
    ('REVIEWER','LIB','MCPS',       TRUE),
    ('REVIEWER','LIB','AGENTS',     TRUE),
    ('REVIEWER','LIB','FLOWS',      TRUE),
    ('REVIEWER','LIB','SKILLS',     TRUE),
    ('REVIEWER','LIB','ASSISTANTS', TRUE),
    ('REVIEWER','LIB','RAG_APPS',   TRUE),
    ('REVIEWER','LIB','MODELS',     TRUE),

    -- Independent options (read-only)
    ('REVIEWER','TAXO', 'TAXONOMY',   FALSE),
    ('REVIEWER','INITS','EXPLORE',    FALSE),
    ('REVIEWER','ANA',  'CATALOG',    FALSE),
    ('REVIEWER','PROC', 'VALUE_CHAIN',FALSE),
    ('REVIEWER','PROC', 'MAP',        FALSE);

-- **********************************
-- ********** Table Units ***********
-- **********************************

INSERT INTO business_units (code, name, description, type, parent) VALUES
    -- Apex
    ('CORP',     'Corporate',           'Corporate Unit',                                  'BUSINESS_UNIT', NULL),

    -- Departments (report to CORP)
    ('ENG',      'Engineering',         'Engineering Department',                          'DEPARTMENT',    'CORP'),
    ('PROD',     'Product & Design',    'Product management and product/UX design',        'DEPARTMENT',    'CORP'),
    ('GTM',      'Commercial',          'Go-to-market: sales and marketing',               'DEPARTMENT',    'CORP'),
    ('PEOPLE',   'People & Culture',    'Talent, recruiting and people operations',        'DEPARTMENT',    'CORP'),
    ('FINOPS',   'Finance & Operations','Finance, administration and corporate operations','DEPARTMENT',    'CORP'),

    -- Areas under Engineering
    ('GEN_AI',   'Generative AI',       'Generative AI',                                   'AREA',          'ENG'),
    ('BACKEND',  'Backend Engineering', 'Server-side services and APIs',                   'AREA',          'ENG'),
    ('FRONTEND', 'Frontend Engineering','Web and client applications',                     'AREA',          'ENG'),
    ('PLATFORM', 'Platform & DevOps',   'Infrastructure, CI/CD and SRE',                   'AREA',          'ENG'),
    ('QA_ENG',   'Quality Assurance',   'Test automation and quality engineering',         'AREA',          'ENG'),

    -- Areas under Product & Design
    ('PM',       'Product Management',  'Product strategy, discovery and roadmap',         'AREA',          'PROD'),
    ('DESIGN',   'Design & UX',         'Product design, UX research and UI',              'AREA',          'PROD'),

    -- Areas under Commercial
    ('SALES',    'Sales',               'Account executives and business development',     'AREA',          'GTM'),
    ('MKT',      'Marketing',           'Demand generation, brand and content',            'AREA',          'GTM');

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

SELECT setval(pg_get_serial_sequence('users', 'id'), GREATEST((SELECT MAX(id) FROM users), 1), false);