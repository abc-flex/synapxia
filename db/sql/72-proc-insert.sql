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

-- ===== Primary value chain sequence (source DEPENDS_ON target) =====
INSERT INTO related_processes (source, target, type, rationale) VALUES
    ('OPER', 'INBL', 'DEPENDS_ON', 'Operations consume the components and code intake from inbound logistics.'),
    ('OUTL', 'OPER', 'DEPENDS_ON', 'Outbound delivery depends on the software produced by operations.'),
    ('MKTS', 'OUTL', 'DEPENDS_ON', 'Marketing & sales rely on products delivered by outbound logistics.'),
    ('SERV', 'MKTS', 'DEPENDS_ON', 'Service follows the customer relationships created by marketing & sales.');

-- ===== Support activities enabling primary ones (source USED_BY target) =====
INSERT INTO related_processes (source, target, type, rationale) VALUES
    ('TECH', 'OPER', 'USED_BY', 'Technology development is leveraged by operations to build software.'),
    ('PROC', 'INBL', 'USED_BY', 'Procurement supplies the inputs consumed by inbound logistics.'),
    ('HRMG', 'OPER', 'USED_BY', 'Human resource management staffs the operations teams.'),
    ('INFR', 'SERV', 'USED_BY', 'Firm infrastructure governs and supports the service activity.');

-- **********************************
-- ********* Process Assets **********
-- **********************************

INSERT INTO process_assets (process, asset, rationale) VALUES
    ('OPER-DEVELOP', 1, 'Python web development prompt used during software development.'),
    ('OPER-DEVELOP', 3, 'Python web developer agent supporting the development process.'),
    ('INBL-CODEMGT', 2, 'GitHub MCP server backing centralized source code management.'),
    ('TECH-AIPLATF', 2, 'GitHub MCP server reused while building AI platform tooling.');

-- **********************************
-- ********* Process Inits ***********
-- **********************************

INSERT INTO process_inits (process, init, rationale) VALUES
    ('TECH-RESEARC', 1, 'R&D drives the Organizational Knowledge Management Platform.'),
    ('INFR-GOVERNA', 2, 'Governance oversees the Centralized Knowledge Base.'),
    ('TECH-AIPLATF', 3, 'AI platform engineering powers the Knowledge Assistant (RAG).'),
    ('HRMG-LEARNIN', 4, 'Learning & development owns the Onboarding Knowledge Hub.'),
    ('SERV-COMMUNI', 5, 'Community engagement sustains the Community of Practice & Expert Directory.');
