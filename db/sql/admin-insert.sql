-- **********************************
-- ********* Table modules **********
-- **********************************

INSERT INTO modules (code, name, description, sort_order) VALUES
    ('Administration',
     'Administration and configuration of the platform.',
     'Administration centralizes security, reference data and structural configuration of SynapxIA, ensuring consistent behavior across modules, user profiles and environments.',
     10),
    ('Collaboration',
     'Collaboration spaces and teamwork.',
     'Collaboration provides shared spaces, teams and structures so people can coordinate work, track progress and align around AI adoption initiatives across the organization.',
     20),
    ('Generative AI',
     'Generative AI assets, prompts, flows and agents.',
     'Generative AI groups the core GenAI capabilities of SynapxIA, including prompt galleries, MCP integrations, flows, models and agents to design and operate AI-powered solutions.',
     30),
    ('AI Initiatives',
     'Lifecycle of AI initiatives and proposals.',
     'AI Initiatives supports the full lifecycle of AI ideas and projects, from proposal and exploration to decision making, tracking and promotion into reusable assets.',
     40),
    ('Digital Assets',
     'Management and exploration of digital assets.',
     'Digital Assets manages the catalog, characterization and evolution of key digital assets, enabling reuse, governance and alignment with AI initiatives and business needs.',
     50),
    ('GenAI Metrics',
     'Monitoring and analysis of Generative AI impact.',
     'GenAI Metrics consolidates KPIs, dashboards and reports that measure the adoption, usage and value of Generative AI across the organization and its processes.',
     60),
    ('Processes',
     'Value chain and business processes.',
     'Processes maps the value chain and key process models of the organization, connecting them with AI initiatives, digital assets and GenAI metrics for continuous improvement.',
     70);

-- **********************************
-- ********* Table options **********
-- **********************************

-- Module: Administration
INSERT INTO options (module, code, name, description, sort_order, type) VALUES
    ('Administration',
     'Roles',
     'Manage system roles and their permissions.',
     'Configuration area to define and maintain the roles available in SynapxIA, documenting their responsibilities and controlling which modules and options they can access.',
     10, 'FORM'),
    ('Administration',
     'Users',
     'Manage platform users and their access.',
     'Interface to register, update and deactivate users, manage their login identifiers and associate them with roles or profiles according to organizational governance policies.',
     20, 'FORM'),
    ('Administration',
     'Lists',
     'Configure parameterized lists used across the system.',
     'Console to manage configurable lists and catalogs used in forms and pop-ups, allowing administrators to adjust values without code changes and keep data consistent.',
     30, 'FORM'),
    ('Administration',
     'Modules',
     'Manage application modules and their metadata.',
     'Administration view to register, describe and order modules, controlling how the main navigation of SynapxIA is presented and which modules are visible to users.',
     40, 'FORM'),
    ('Administration',
     'Options',
     'Manage application options and navigation items.',
     'Tool to configure options within each module, including labels, grouping and visibility, so the menu structure reflects the needs of different roles and journeys.',
     50, 'FORM');

-- Module: Collaboration
INSERT INTO options (module, code, name, description, sort_order, type) VALUES
    ('Collaboration',
     'Teams',
     'Manage collaboration teams and groups.',
     'Area to create and maintain cross-functional teams, assign members and define their roles, providing a shared context for working on AI initiatives and digital assets.',
     10, 'FORM'),
    ('Collaboration',
     'Projects',
     'Organize collaboration around specific projects.',
     'Space to register and follow AI-related projects or workstreams, linking teams, initiatives and assets so collaboration happens around clear, shared objectives.',
     20, 'FORM'),
    ('Collaboration',
     'Dimensions',
     'Define collaboration and analysis dimensions.',
     'Configuration view to define dimensions such as domain, business unit or maturity, which can be used to segment, filter and analyze collaborative work in SynapxIA.',
     30, 'FORM'),
    ('Collaboration',
     'Assignments Dashboard',
     'Visualize assignments, status and workload.',
     'Dashboard that consolidates tasks, responsibilities and pending actions across teams and projects, helping balance workload and monitor collaboration progress.',
     40, 'FORM');

-- Module: Generative AI
INSERT INTO options (module, code, name, description, sort_order, type) VALUES
    ('Generative AI',
     'Prompt Gallery',
     'Manage reusable prompts for Generative AI.',
     'Central gallery where curated prompts are created, documented and shared, encouraging reuse of proven prompt patterns and governance of how GenAI is used in practice.',
     10, 'FORM'),
    ('Generative AI',
     'MCPs Catalog',
     'Catalog of MCP-based tools and integrations.',
     'Repository of tools and integrations compatible with the Model Context Protocol (MCP), documenting capabilities, configuration details and recommended usage scenarios.',
     20, 'FORM'),
    ('Generative AI',
     'AI Flows',
     'Design and orchestrate AI-powered flows.',
     'Workspace to design multi-step AI flows that connect prompts, tools, models and business rules, enabling reusable patterns that can be aligned with enterprise processes.',
     30, 'FORM'),
    ('Generative AI',
     'RAG Applications',
     'Manage Retrieval-Augmented Generation applications.',
     'Module to configure, monitor and evolve RAG use cases, connecting data sources, defining retrieval strategies and following up on quality and behavior of GenAI outputs.',
     40, 'FORM'),
    ('Generative AI',
     'Models',
     'Manage and catalogue AI/ML models.',
     'Catalog of AI and ML models used in SynapxIA, including ownership, purpose, constraints and integration points, helping standardize and govern model usage.',
     50, 'FORM'),
    ('Generative AI',
     'Assistants',
     'Configure AI assistants for specific use cases.',
     'Configuration area for AI assistants oriented to well-defined use cases such as support, documentation or ideation, specifying their scope, tone, tools and guardrails.',
     60, 'FORM'),
    ('Generative AI',
     'Agents',
     'Configure autonomous or semi-autonomous AI agents.',
     'Module to design agents with higher autonomy, defining their goals, allowed actions, monitoring signals and escalation paths, so they remain aligned with business constraints.',
     70, 'FORM'),
    ('Generative AI',
     'N8n',
     'Integrations and workflows orchestrated via n8n.',
     'Space dedicated to workflows and automations built with n8n, documenting connectors, triggers and orchestrations that extend GenAI capabilities with external systems.',
     80, 'FORM');

-- Module: AI Initiatives
INSERT INTO options (module, code, name, description, sort_order, type) VALUES
    ('AI Initiatives',
     'Proposal',
     'Register new AI initiative proposals.',
     'Entry point to capture new AI initiative proposals with key information such as problem statement, expected value, sponsors, impacted processes and initial assumptions.',
     10, 'FORM'),
    ('AI Initiatives',
     'Explore',
     'Explore and filter AI initiatives.',
     'View that lets stakeholders browse and filter the portfolio of AI initiatives by status, domain, value or risk, supporting transparency and alignment across the organization.',
     20, 'FORM'),
    ('AI Initiatives',
     'Promote to Asset',
     'Promote initiatives to reusable digital assets.',
     'Functionality to convert a matured AI initiative into one or more reusable assets (such as models, flows or prompts), linking them back to the original business context.',
     30, 'FORM');

-- Module: Digital Assets
INSERT INTO options (module, code, name, description, sort_order, type) VALUES
    ('Digital Assets',
     'Categories',
     'Define categories for organizing digital assets.',
     'Configuration area to define and maintain the taxonomy of digital asset categories, helping users understand where to register and find information within SynapxIA.',
     10, 'FORM'),
    ('Digital Assets',
     'Characteristics',
     'Define attributes and characteristics of assets.',
     'Administrative view to define metadata and attributes that describe assets (such as sensitivity, lifecycle or domain), enabling richer search and better governance.',
     20, 'FORM'),
    ('Digital Assets',
     'Asset Catalog',
     'Central catalog of registered digital assets.',
     'Catalog that consolidates the inventory of relevant digital assets, linking them to owners, initiatives and processes so they can be reused and evolved over time.',
     30, 'FORM');

-- Module: GenAI Metrics
INSERT INTO options (module, code, name, description, sort_order, type) VALUES
    ('GenAI Metrics',
     'GenAI KPIs',
     'Define and monitor key GenAI KPIs.',
     'Module to define, calculate and track key performance indicators related to Generative AI usage, impact and quality across initiatives, teams and processes.',
     10, 'FORM'),
    ('GenAI Metrics',
     'GenAI Dashboards',
     'Visualize GenAI metrics through dashboards.',
     'Set of dashboards that consolidate GenAI-related metrics into visual stories, enabling leaders to quickly understand adoption, performance and areas of opportunity.',
     20, 'FORM'),
    ('GenAI Metrics',
     'GenAI Reports',
     'Generate and distribute GenAI analytical reports.',
     'Functionality to build, schedule and share reports about Generative AI adoption and outcomes, supporting regular communication with stakeholders and governance bodies.',
     30, 'FORM');

-- Module: Processes
INSERT INTO options (module, code, name, description, sort_order, type) VALUES
    ('Processes',
     'Value Chain',
     'Model and manage the organizational value chain.',
     'View dedicated to modeling the value chain, identifying stages where AI and digital assets can create impact and connecting them with initiatives and metrics.',
     10, 'FORM'),
    ('Processes',
     'Processes Map',
     'Provide a high-level map of processes.',
     'Representation of the main process landscape, showing how processes are grouped and related and where AI initiatives or assets are expected to intervene.',
     20, 'FORM'),
    ('Processes',
     'Processes Models',
     'Detail and manage specific process models.',
     'Module to document detailed process models, relate them to assets, initiatives and GenAI metrics, and use them as a reference for continuous improvement and automation.',
     30, 'FORM');


-- **********************************
-- ********** Table roles ***********
-- **********************************

INSERT INTO roles (code, name, description, is_active)
VALUES
    ('Administrator',
     'Platform Administrator',
     'Full access to all modules and options in SynapxIA, including configuration, security and operational capabilities.',
     TRUE),
    ('Administrative',
     'Operational Administrator',
     'Administrative role with full edit access to collaboration, Generative AI, AI initiatives, metrics, processes and digital assets, but without platform-level administration features.',
     TRUE),
    ('Collaborator',
     'Standard Collaborator',
     'Operational user with read access to collaboration, Generative AI, AI initiatives, processes and digital assets, and edit rights only for AI initiative proposals.',
     TRUE);

-- **********************************
-- ******** Table privileges ********
-- **********************************

INSERT INTO privileges (role, module, option, can_edit)
VALUES
    -- Administration
    ('Administrator', 'Administration', 'Roles',              TRUE),
    ('Administrator', 'Administration', 'Users',              TRUE),
    ('Administrator', 'Administration', 'Lists',              TRUE),
    ('Administrator', 'Administration', 'Modules',            TRUE),
    ('Administrator', 'Administration', 'Options',            TRUE),

    -- Collaboration
    ('Administrator', 'Collaboration', 'Teams',               TRUE),
    ('Administrator', 'Collaboration', 'Projects',            TRUE),
    ('Administrator', 'Collaboration', 'Dimensions',          TRUE),
    ('Administrator', 'Collaboration', 'Assignments Dashboard', TRUE),

    -- Generative AI
    ('Administrator', 'Generative AI', 'Prompt Gallery',      TRUE),
    ('Administrator', 'Generative AI', 'MCPs Catalog',        TRUE),
    ('Administrator', 'Generative AI', 'AI Flows',            TRUE),
    ('Administrator', 'Generative AI', 'RAG Applications',    TRUE),
    ('Administrator', 'Generative AI', 'Models',              TRUE),
    ('Administrator', 'Generative AI', 'Assistants',          TRUE),
    ('Administrator', 'Generative AI', 'Agents',              TRUE),
    ('Administrator', 'Generative AI', 'N8n',                 TRUE),

    -- AI Initiatives
    ('Administrator', 'AI Initiatives', 'Proposal',           TRUE),
    ('Administrator', 'AI Initiatives', 'Explore',            TRUE),
    ('Administrator', 'AI Initiatives', 'Promote to Asset',   TRUE),

    -- Digital Assets
    ('Administrator', 'Digital Assets', 'Categories',         TRUE),
    ('Administrator', 'Digital Assets', 'Characteristics',    TRUE),
    ('Administrator', 'Digital Assets', 'Asset Catalog',      TRUE),

    -- GenAI Metrics
    ('Administrator', 'GenAI Metrics', 'GenAI KPIs',          TRUE),
    ('Administrator', 'GenAI Metrics', 'GenAI Dashboards',    TRUE),
    ('Administrator', 'GenAI Metrics', 'GenAI Reports',       TRUE),

    -- Processes
    ('Administrator', 'Processes', 'Value Chain',             TRUE),
    ('Administrator', 'Processes', 'Processes Map',           TRUE),
    ('Administrator', 'Processes', 'Processes Models',        TRUE);

INSERT INTO privileges (role, module, option, can_edit)
VALUES
    -- Collaboration
    ('Administrative', 'Collaboration', 'Teams',               TRUE),
    ('Administrative', 'Collaboration', 'Projects',            TRUE),
    ('Administrative', 'Collaboration', 'Dimensions',          TRUE),
    ('Administrative', 'Collaboration', 'Assignments Dashboard', TRUE),

    -- Generative AI
    ('Administrative', 'Generative AI', 'Prompt Gallery',      TRUE),
    ('Administrative', 'Generative AI', 'MCPs Catalog',        TRUE),
    ('Administrative', 'Generative AI', 'AI Flows',            TRUE),
    ('Administrative', 'Generative AI', 'RAG Applications',    TRUE),
    ('Administrative', 'Generative AI', 'Models',              TRUE),
    ('Administrative', 'Generative AI', 'Assistants',          TRUE),
    ('Administrative', 'Generative AI', 'Agents',              TRUE),
    ('Administrative', 'Generative AI', 'N8n',                 TRUE),

    -- AI Initiatives
    ('Administrative', 'AI Initiatives', 'Proposal',           TRUE),
    ('Administrative', 'AI Initiatives', 'Explore',            TRUE),
    ('Administrative', 'AI Initiatives', 'Promote to Asset',   TRUE),

    -- Digital Assets
    ('Administrative', 'Digital Assets', 'Categories',         TRUE),
    ('Administrative', 'Digital Assets', 'Characteristics',    TRUE),
    ('Administrative', 'Digital Assets', 'Asset Catalog',      TRUE),

    -- GenAI Metrics
    ('Administrative', 'GenAI Metrics', 'GenAI KPIs',          TRUE),
    ('Administrative', 'GenAI Metrics', 'GenAI Dashboards',    TRUE),
    ('Administrative', 'GenAI Metrics', 'GenAI Reports',       TRUE),

    -- Processes
    ('Administrative', 'Processes', 'Value Chain',             TRUE),
    ('Administrative', 'Processes', 'Processes Map',           TRUE),
    ('Administrative', 'Processes', 'Processes Models',        TRUE);

INSERT INTO privileges (role, module, option, can_edit)
VALUES
    -- Collaboration (solo lectura)
    ('Collaborator', 'Collaboration', 'Teams',               FALSE),
    ('Collaborator', 'Collaboration', 'Projects',            FALSE),
    ('Collaborator', 'Collaboration', 'Dimensions',          FALSE),
    ('Collaborator', 'Collaboration', 'Assignments Dashboard', FALSE),

    -- Generative AI (solo lectura)
    ('Collaborator', 'Generative AI', 'Prompt Gallery',      FALSE),
    ('Collaborator', 'Generative AI', 'MCPs Catalog',        FALSE),
    ('Collaborator', 'Generative AI', 'AI Flows',            FALSE),
    ('Collaborator', 'Generative AI', 'RAG Applications',    FALSE),
    ('Collaborator', 'Generative AI', 'Models',              FALSE),
    ('Collaborator', 'Generative AI', 'Assistants',          FALSE),
    ('Collaborator', 'Generative AI', 'Agents',              FALSE),
    ('Collaborator', 'Generative AI', 'N8n',                 FALSE),

    -- AI Initiatives
    ('Collaborator', 'AI Initiatives', 'Proposal',           TRUE),
    ('Collaborator', 'AI Initiatives', 'Explore',            FALSE),
    ('Collaborator', 'AI Initiatives', 'Promote to Asset',   FALSE),

    -- Digital Assets (solo lectura)
    ('Collaborator', 'Digital Assets', 'Categories',         FALSE),
    ('Collaborator', 'Digital Assets', 'Characteristics',    FALSE),
    ('Collaborator', 'Digital Assets', 'Asset Catalog',      FALSE),

    -- Processes (solo lectura)
    ('Collaborator', 'Processes', 'Value Chain',             FALSE),
    ('Collaborator', 'Processes', 'Processes Map',           FALSE),
    ('Collaborator', 'Processes', 'Processes Models',        FALSE);

-- **********************************
-- ********** Table users ***********
-- **********************************

INSERT INTO users (
    id,
    username,
    email,
    password_hash,
    first_name,
    last_name,
    status,
    menu_role
) VALUES (
    0,
    'admin',
    'admin@synapxia.dev',
    'SCRAM-SHA-256$4096:erZkGksCVwc49r8o18VeSg==$2c7cw07foNs0h+cLgJYdpcc7da/tjQRH7v5Y8UP0ugo=:yw24DEvmi0xGcE7qj2Y7g+QwCxuoO4q6JhZsaLkzMlg=',
    -- Password: Admin123*
    'Platform',
    'Administrator',
    'Active',
    'Administrator'
);

-- **********************************
-- ***** Table lists/list_items *****
-- **********************************

-- List: List Type
INSERT INTO lists (code, name, description, type, module, is_active)
VALUES (
    'List Type',
    'List types for system configuration',
    'List that classifies the types of lists in two categories: List of Values and Scale.',
    'LIST_OF_VALUES',
    'Administration',
    TRUE
);

INSERT INTO list_items (list, value, label, sort_order, is_active)
VALUES
    ('List Type', 'LIST_OF_VALUES',  'List of Values',  10, TRUE),
    ('List Type', 'SCALE', 'Scale', 20, TRUE);


-- List: Is Active
INSERT INTO lists (code, name, description, type, module, is_active)
VALUES (
    'Is Active',
    'Is Active flag',
    'Boolean flag used to indicate whether an element is active or inactive in SynapxIA.',
    'LIST_OF_VALUES',
    'Administration',
    TRUE
);

INSERT INTO list_items (list, value, label, sort_order, is_active)
VALUES
    ('Is Active', 'TRUE',  'True',  10, TRUE),
    ('Is Active', 'FALSE', 'False', 20, TRUE);

-- List: User Status
INSERT INTO lists (code, name, description, type, module, is_active)
VALUES (
    'User Status',
    'User status values',
    'List of possible status values for users in SynapxIA (active or inactive).',
    'LIST_OF_VALUES',
    'Administration',
    TRUE
);

INSERT INTO list_items (list, value, label, sort_order, is_active)
VALUES
    ('User Status', 'ACTIVE',   'Active',   10, TRUE),
    ('User Status', 'INACTIVE', 'Inactive', 20, TRUE);

-- List: Option Type
INSERT INTO lists (code, name, description, type, module, is_active)
VALUES (
    'Option Type',
    'Option types for navigation items',
    'List that classifies application options by type, such as content pages, forms or reports.',
    'LIST_OF_VALUES',
    'Administration',
     TRUE
);

INSERT INTO list_items (list, value, label, sort_order, is_active)
VALUES
    ('Option Type', 'CONTENT', 'Content', 10, TRUE),
    ('Option Type', 'FORM',    'Form',    20, TRUE),
    ('Option Type', 'REPORT',  'Report',  30, TRUE);

-- List: Project Status
INSERT INTO lists (code, name, description, type, module, is_active)
VALUES (
    'Project Status',
    'Project status values',
    'List of possible status values for Projects in SynapxIA (planned, in progress, on hold or complete).',
    'LIST_OF_VALUES',
    'Collaboration',
    TRUE
);

INSERT INTO list_items (list, value, label, sort_order, is_active)
VALUES
    ('Project Status', 'PLANNED',   'Planned',   10, TRUE),
    ('Project Status', 'IN_PROGRESS', 'In Progress', 20, TRUE),
    ('Project Status', 'ON_HOLD',  'On Hold',  30, TRUE),
    ('Project Status', 'COMPLETED','Completed', 40, TRUE);
