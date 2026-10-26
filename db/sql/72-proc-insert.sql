-- **********************************
-- ******* Tables Processes *********
-- **********************************

-- ===== Support activities =====
INSERT INTO processes (code, name, description, type, parent, unit, owner, status) VALUES
    ('INFR', 'Firm Infrastructure',
     'Matrix structure with strong governance and global oversight; transparency, cost forecasting and ethical AI.',
     'SUPPORT', NULL, 'CORP', 0, 'PUBLISHED'),
    ('HRMG', 'Human Resource Management',
     'Global hiring prioritizing DEI and high-skill development, fostering continuous learning and growth.',
     'SUPPORT', NULL, 'CORP', 0, 'PUBLISHED'),
    ('TECH', 'Technology Development',
     'Heavy R&D in AI, cloud, quantum computing and mixed reality, leading product innovation.',
     'SUPPORT', NULL, 'ENG', 0, 'PUBLISHED'),
    ('PROC', 'Procurement',
     'Centralized procurement for hardware, software and cloud needs with sustainable and ethical sourcing.',
     'SUPPORT', NULL, 'CORP', 0, 'PUBLISHED');

-- ===== Primary activities =====
INSERT INTO processes (code, name, description, type, parent, unit, owner, status) VALUES
    ('INBL', 'Inbound Logistics',
     'Sourcing of hardware components and centralized, just-in-time code management with sustainable intake.',
     'PRIMARY', NULL, 'ENG', 0, 'PUBLISHED'),
    ('OPER', 'Operations',
     'Agile development of software and cloud infrastructure with DevOps and automation at scale.',
     'PRIMARY', NULL, 'ENG', 0, 'PUBLISHED'),
    ('OUTL', 'Outbound Logistics',
     'Digital delivery of software, updates and subscriptions, plus global device distribution.',
     'PRIMARY', NULL, 'ENG', 0, 'PUBLISHED'),
    ('MKTS', 'Marketing & Sales',
     'Multichannel marketing and sales through digital ads, partners and enterprise teams.',
     'PRIMARY', NULL, 'CORP', 0, 'PUBLISHED'),
    ('SERV', 'Service',
     'Extensive customer support, technical guidance, monitoring and community engagement.',
     'PRIMARY', NULL, 'ENG', 0, 'PUBLISHED');

-- **********************************
-- ************ Processes ***********
-- **********************************

-- ===== INFR - Firm Infrastructure (support) =====
INSERT INTO processes (code, name, description, type, parent, unit, owner, status) VALUES
    ('INFR-GOVERNA', 'Corporate Governance',
     'Matrix governance, global oversight and corporate compliance.',
     'SUPPORT', 'INFR', 'CORP', 0, 'PUBLISHED'),
    ('INFR-FINPLAN', 'Financial Planning',
     'Budgeting, cost forecasting and transparent financial control.',
     'SUPPORT', 'INFR', 'CORP', 0, 'PUBLISHED'),
    ('INFR-ETHICAI', 'Ethical AI Oversight',
     'Responsible-AI principles, risk review and ethical guardrails.',
     'SUPPORT', 'INFR', 'CORP', 0, 'PUBLISHED');

-- ===== HRMG - Human Resource Management (support) =====
INSERT INTO processes (code, name, description, type, parent, unit, owner, status) VALUES
    ('HRMG-RECRUIT', 'Talent Acquisition',
     'Global hiring prioritizing DEI and specialized technical skills.',
     'SUPPORT', 'HRMG', 'CORP', 0, 'PUBLISHED'),
    ('HRMG-LEARNIN', 'Learning & Development',
     'Upskilling through platforms such as Microsoft Learn and LinkedIn Learning.',
     'SUPPORT', 'HRMG', 'CORP', 0, 'PUBLISHED'),
    ('HRMG-PEOPLEM', 'People Management',
     'Performance, retention and organizational growth of teams.',
     'SUPPORT', 'HRMG', 'CORP', 0, 'PUBLISHED');

-- ===== TECH - Technology Development (support) =====
INSERT INTO processes (code, name, description, type, parent, unit, owner, status) VALUES
    ('TECH-RESEARC', 'Research & Development',
     'R&D in AI, cloud, quantum computing and mixed reality.',
     'SUPPORT', 'TECH', 'ENG', 0, 'PUBLISHED'),
    ('TECH-AIPLATF', 'AI Platform Engineering',
     'Building AI platforms such as GitHub Copilot and Azure OpenAI.',
     'SUPPORT', 'TECH', 'ENG', 0, 'PUBLISHED'),
    ('TECH-ARCHITE', 'Architecture & Standards',
     'Reference architectures, engineering standards and tech governance.',
     'SUPPORT', 'TECH', 'ENG', 0, 'PUBLISHED');

-- ===== PROC - Procurement (support) =====
INSERT INTO processes (code, name, description, type, parent, unit, owner, status) VALUES
    ('PROC-SOURCIN', 'Strategic Sourcing',
     'Centralized sourcing of hardware, software and cloud capacity.',
     'SUPPORT', 'PROC', 'CORP', 0, 'PUBLISHED'),
    ('PROC-VENDORM', 'Vendor Management',
     'Supplier onboarding, contracts and quality assurance.',
     'SUPPORT', 'PROC', 'CORP', 0, 'PUBLISHED'),
    ('PROC-SUSTAIN', 'Sustainable Sourcing',
     'Sustainability, ethical sourcing and responsible supply chain.',
     'SUPPORT', 'PROC', 'CORP', 0, 'PUBLISHED');

-- ===== INBL - Inbound Logistics (primary) =====
INSERT INTO processes (code, name, description, type, parent, unit, owner, status) VALUES
    ('INBL-COMPSRC', 'Component Sourcing',
     'Sourcing of hardware components for devices such as Surface and Xbox.',
     'PRIMARY', 'INBL', 'ENG', 0, 'PUBLISHED'),
    ('INBL-CODEMGT', 'Source Code Management',
     'Just-in-time delivery and centralized code management via GitHub.',
     'PRIMARY', 'INBL', 'ENG', 0, 'PUBLISHED'),
    ('INBL-DEPENDM', 'Dependency Management',
     'Management of libraries, packages and third-party dependencies.',
     'PRIMARY', 'INBL', 'ENG', 0, 'PUBLISHED');

-- ===== OPER - Operations (primary) =====
INSERT INTO processes (code, name, description, type, parent, unit, owner, status) VALUES
    ('OPER-DEVELOP', 'Software Development',
     'Agile development for software like Windows, 365 and Azure.',
     'PRIMARY', 'OPER', 'ENG', 0, 'PUBLISHED'),
    ('OPER-CLOUDIN', 'Cloud Infrastructure',
     'Cloud infrastructure across 60+ regions for global scalability.',
     'PRIMARY', 'OPER', 'ENG', 0, 'PUBLISHED'),
    ('OPER-DEVOPSA', 'DevOps & Automation',
     'DevOps practices and automation in software and device production.',
     'PRIMARY', 'OPER', 'ENG', 0, 'PUBLISHED'),
    ('OPER-QUALITY', 'Quality Assurance',
     'Testing, quality gates and reliability engineering.',
     'PRIMARY', 'OPER', 'ENG', 0, 'PUBLISHED');

-- ===== OUTL - Outbound Logistics (primary) =====
INSERT INTO processes (code, name, description, type, parent, unit, owner, status) VALUES
    ('OUTL-RELEASE', 'Release Management',
     'Digital delivery of software, updates and subscriptions.',
     'PRIMARY', 'OUTL', 'ENG', 0, 'PUBLISHED'),
    ('OUTL-DEPLOYM', 'Deployment & Delivery',
     'Azure CDN-accelerated content delivery and software deployment.',
     'PRIMARY', 'OUTL', 'ENG', 0, 'PUBLISHED'),
    ('OUTL-DISTRIB', 'Device Distribution',
     'Global logistics for devices via retail and e-commerce.',
     'PRIMARY', 'OUTL', 'ENG', 0, 'PUBLISHED');

-- ===== MKTS - Marketing & Sales (primary) =====
INSERT INTO processes (code, name, description, type, parent, unit, owner, status) VALUES
    ('MKTS-DIGMKTG', 'Digital Marketing',
     'Multichannel digital advertising across web, partners and social.',
     'PRIMARY', 'MKTS', 'CORP', 0, 'PUBLISHED'),
    ('MKTS-CAMPAIG', 'Campaign Management',
     'Campaigns focused on security, productivity and innovation.',
     'PRIMARY', 'MKTS', 'CORP', 0, 'PUBLISHED'),
    ('MKTS-SALESOP', 'Sales Operations',
     'Enterprise sales, bundling and continuous-update loyalty.',
     'PRIMARY', 'MKTS', 'CORP', 0, 'PUBLISHED'),
    ('MKTS-PARTNER', 'Partner Channel',
     'Partner ecosystem and channel-driven go-to-market.',
     'PRIMARY', 'MKTS', 'CORP', 0, 'PUBLISHED');

-- ===== SERV - Service (primary) =====
INSERT INTO processes (code, name, description, type, parent, unit, owner, status) VALUES
    ('SERV-SUPPORT', 'Customer Support',
     'Support via chatbots, help centers and premium tiers.',
     'PRIMARY', 'SERV', 'ENG', 0, 'PUBLISHED'),
    ('SERV-MONITOR', 'Monitoring & Maintenance',
     'Technical guidance, Azure monitoring and frequent updates.',
     'PRIMARY', 'SERV', 'ENG', 0, 'PUBLISHED'),
    ('SERV-COMMUNI', 'Community Engagement',
     'Community engagement through Xbox Live and Microsoft 365.',
     'PRIMARY', 'SERV', 'ENG', 0, 'PUBLISHED');

-- **********************************
-- ******** Related Processes *******
-- **********************************

-- ===== Primary value chain sequence (source PRECEDES target) =====
INSERT INTO related_processes (source, target, type, rationale) VALUES
    ('INBL', 'OPER', 'PRECEDES', 'Inbound logistics delivers the components and code intake that operations consume.'),
    ('OPER', 'OUTL', 'PRECEDES', 'Operations produce the software that outbound logistics delivers.'),
    ('OUTL', 'MKTS', 'PRECEDES', 'Outbound logistics delivers the products that marketing & sales bring to customers.'),
    ('MKTS', 'SERV', 'PRECEDES', 'Marketing & sales create the customer relationships that service follows up.');

-- ===== Support activities enabling primary ones (source SUPPORTS target) =====
INSERT INTO related_processes (source, target, type, rationale) VALUES
    ('TECH', 'OPER', 'SUPPORTS', 'Technology development is leveraged by operations to build software.'),
    ('PROC', 'INBL', 'SUPPORTS', 'Procurement supplies the inputs consumed by inbound logistics.'),
    ('HRMG', 'OPER', 'SUPPORTS', 'Human resource management staffs the operations teams.'),
    ('INFR', 'SERV', 'SUPPORTS', 'Firm infrastructure governs and supports the service activity.');

-- ===== Inside each activity: the flow between its sub-processes =====
-- (drawn by the Process Map's internal diagrams, specs/010-process-landscape-views;
-- PRECEDES only between processes of the same type, SUPPORTS only Support → Primary)
INSERT INTO related_processes (source, target, type, rationale) VALUES
    -- Inbound Logistics
    ('INBL-COMPSRC', 'INBL-DEPENDM', 'PRECEDES', 'Sourced components are registered as managed dependencies.'),
    ('INBL-CODEMGT', 'INBL-DEPENDM', 'PRECEDES', 'Code intake is followed by dependency resolution and pinning.'),
    -- Operations
    ('OPER-DEVELOP', 'OPER-QUALITY', 'PRECEDES', 'Developed software goes through quality assurance.'),
    ('OPER-QUALITY', 'OPER-DEVOPSA', 'PRECEDES', 'Validated builds enter the automated delivery pipeline.'),
    ('OPER-CLOUDIN', 'OPER-DEVOPSA', 'PRECEDES', 'Provisioned infrastructure is ready before pipelines deploy to it.'),
    ('OPER-DEVOPSA', 'OPER-DEVELOP', 'FEEDS_INTO', 'Pipeline telemetry feeds back into development.'),
    -- Outbound Logistics
    ('OUTL-RELEASE', 'OUTL-DEPLOYM', 'PRECEDES', 'A cut release is deployed and delivered digitally.'),
    ('OUTL-RELEASE', 'OUTL-DISTRIB', 'PRECEDES', 'A cut release is shipped on devices.'),
    -- Marketing & Sales
    ('MKTS-DIGMKTG', 'MKTS-CAMPAIG', 'PRECEDES', 'Digital marketing insight shapes the campaigns.'),
    ('MKTS-CAMPAIG', 'MKTS-SALESOP', 'PRECEDES', 'Campaign leads are worked by sales operations.'),
    ('MKTS-PARTNER', 'MKTS-SALESOP', 'INTERACTS_WITH', 'Partners and sales operations coordinate shared deals.'),
    -- Service
    ('SERV-MONITOR', 'SERV-SUPPORT', 'PRECEDES', 'Monitoring detects the issues that customer support resolves.'),
    ('SERV-SUPPORT', 'SERV-COMMUNI', 'PRECEDES', 'Resolved cases feed community knowledge and engagement.'),
    -- Firm Infrastructure
    ('INFR-FINPLAN', 'INFR-GOVERNA', 'PRECEDES', 'Financial plans are approved through corporate governance.'),
    ('INFR-GOVERNA', 'INFR-ETHICAI', 'PRECEDES', 'Governance decisions are reviewed for ethical AI compliance.'),
    -- Human Resource Management
    ('HRMG-RECRUIT', 'HRMG-LEARNIN', 'PRECEDES', 'New hires enter the learning and onboarding programs.'),
    ('HRMG-LEARNIN', 'HRMG-PEOPLEM', 'PRECEDES', 'Developed people are managed for performance and growth.'),
    -- Technology Development
    ('TECH-RESEARC', 'TECH-ARCHITE', 'PRECEDES', 'Research results become architecture standards.'),
    ('TECH-ARCHITE', 'TECH-AIPLATF', 'PRECEDES', 'Standards guide how the AI platform is built.'),
    -- Procurement
    ('PROC-SOURCIN', 'PROC-VENDORM', 'PRECEDES', 'Selected suppliers are onboarded into vendor management.'),
    ('PROC-SUSTAIN', 'PROC-SOURCIN', 'GOVERNS', 'Sustainability criteria constrain sourcing decisions.');

-- ===== Between sub-processes of different activities =====
INSERT INTO related_processes (source, target, type, rationale) VALUES
    ('INBL-CODEMGT', 'OPER-DEVELOP', 'FEEDS_INTO', 'Managed source code is the input of development.'),
    ('OPER-DEVOPSA', 'OUTL-RELEASE', 'PRECEDES', 'Pipelines produce the builds that release management cuts.'),
    ('OUTL-DEPLOYM', 'SERV-MONITOR', 'TRIGGERS', 'Each deployment starts its monitoring.'),
    ('MKTS-SALESOP', 'SERV-SUPPORT', 'TRIGGERS', 'A closed sale opens the customer support relationship.'),
    ('TECH-AIPLATF', 'OPER-DEVELOP', 'SUPPORTS', 'The AI platform provides the tooling developers use.'),
    ('HRMG-LEARNIN', 'OPER-DEVELOP', 'SUPPORTS', 'Learning programs upskill the development teams.'),
    ('PROC-VENDORM', 'INBL-COMPSRC', 'SUPPORTS', 'Vendor management keeps component suppliers available.'),
    ('INFR-ETHICAI', 'TECH-AIPLATF', 'GOVERNS', 'Ethical AI oversight sets guardrails for the AI platform.');

-- **********************************
-- ********* Process Assets **********
-- **********************************

INSERT INTO process_assets (process, asset, type, rationale) VALUES
    ('OPER-DEVELOP', 1, 'RELATED_TO', 'Python web development prompt used during software development.'),
    ('OPER-DEVELOP', 3, 'RELATED_TO', 'Python web developer agent supporting the development process.'),
    ('INBL-CODEMGT', 2, 'RELATED_TO', 'GitHub MCP server backing centralized source code management.'),
    ('TECH-AIPLATF', 2, 'RELATED_TO', 'GitHub MCP server reused while building AI platform tooling.');

-- **********************************
-- ********* Process Inits ***********
-- **********************************

INSERT INTO process_inits (process, init, type, rationale) VALUES
    ('TECH-RESEARC', 1, 'RELATED_TO', 'R&D drives the Organizational Knowledge Management Platform.'),
    ('INFR-GOVERNA', 2, 'RELATED_TO', 'Governance oversees the Centralized Knowledge Base.'),
    ('TECH-AIPLATF', 3, 'RELATED_TO', 'AI platform engineering powers the Knowledge Assistant (RAG).'),
    ('HRMG-LEARNIN', 4, 'RELATED_TO', 'Learning & development owns the Onboarding Knowledge Hub.'),
    ('SERV-COMMUNI', 5, 'RELATED_TO', 'Community engagement sustains the Community of Practice & Expert Directory.');
