-- **********************************
-- ******** Table Criterias *********
-- **********************************

INSERT INTO criterias (code, name, description, list) VALUES
('CLARITY_MATURITY', 'Clarity and maturity of the need', 'Level of definition of the need', 'CLARITY_MATURITY'),
('SUPPORT_OBJECTIVE', 'Support objective', 'Type of support required', 'SUPPORT_OBJECTIVE'),
('COMPLEXITY', 'Technical and functional complexity', 'Level of solution complexity', 'COMPLEXITY'),
('DATA_INTEGRATIONS', 'Data and integrations', 'Use of data and integrations', 'DATA_INTEGRATIONS'),
('RISK_IMPACT', 'Operational risk and impact', 'Level of operational risk', 'RISK_IMPACT'),
('SUSTAINABILITY', 'Sustainability and expected adoption level', 'Level of usage and adoption', 'SUSTAINABILITY');

-- **********************************
-- ******* Table initiatives ********
-- **********************************

INSERT INTO initiatives (id, name, description, expected_impact, priority_level, reference, status, tags, detail, score) VALUES
    (1, 'Organizational Knowledge Management Platform',
     'Develop a centralized platform to capture, organize, share and reuse the organization''s knowledge, reducing information silos and accelerating decision-making.',
     'DECISION_SUPPORT', 'HIGH', 'https://wiki.synapxia.local/initiatives/knowledge-management',
     '3-ENGAGING', '["knowledge-management", "platform", "collaboration", "genai"]',
     $$# Organizational Knowledge Management Platform

## Problem
Critical knowledge is scattered across chats, drives, email threads and individual
expertise. New hires take weeks to find what they need and teams repeatedly solve
problems that were already solved elsewhere.

## Goal
A single platform where knowledge is captured close to where work happens,
classified through the asset taxonomy, made searchable, and surfaced proactively
through a GenAI assistant.

## Scope (MVP)
1. Structured knowledge base with categories, tags and ownership.
2. Full-text + semantic search over all documented assets.
3. GenAI assistant (RAG) that answers questions citing internal sources.
4. Contribution and review workflow with lightweight governance.

## Out of scope (for now)
- Migration of legacy archives older than 3 years.
- External (customer-facing) knowledge portal.
$$, 16),
    (2, 'Centralized Knowledge Base',
     'Single repository to document, categorize and version the organization''s explicit knowledge, replacing scattered drives and wikis.',
     'QUALITY_IMPROVEMENT', 'HIGH', NULL,
     '4-DELIVERED', '["knowledge-base", "documentation", "taxonomy"]',
     'Foundational repository that feeds the rest of the platform. Articles are classified using the existing asset taxonomy and reuse the lists/list_items catalog for status and visibility.',
     14),
    (3, 'Knowledge Assistant (RAG)',
     'GenAI assistant that answers employee questions in natural language, retrieving and citing content from the centralized knowledge base.',
     'TIME_REDUCTION', 'HIGH', NULL,
     '3-ENGAGING', '["genai", "rag", "assistant", "search"]',
     'Retrieval-augmented assistant on top of the knowledge base. Requires the knowledge base (initiative 2) to be populated before it can deliver value.',
     15),
    (4, 'Onboarding Knowledge Hub',
     'Curated onboarding paths that guide new hires through the knowledge they need in their first 30/60/90 days.',
     'IMPROVED_UX', 'MEDIUM', NULL,
     '2-ASSESSMENT', '["onboarding", "enablement", "knowledge-management"]',
     'Consumes content from the centralized knowledge base and tailors learning paths per role and team.',
     NULL),
    (5, 'Community of Practice & Expert Directory',
     'Directory of internal experts and spaces for communities of practice to capture tacit knowledge through Q&A and discussions.',
     'INNOVATION', 'LOW', NULL,
     '1-ACTIVATED', '["community", "experts", "tacit-knowledge"]',
     'Turns tacit, person-bound knowledge into reusable assets by connecting questions to the right people and curating the best answers back into the knowledge base.',
     NULL);

-- Keep the identity sequence aligned with the explicit ids above
SELECT setval(pg_get_serial_sequence('initiatives', 'id'), (SELECT MAX(id) FROM initiatives));

-- **********************************
-- ******* Table diagnostics ********
-- **********************************

INSERT INTO diagnostics (init, criteria, creator_score, reviewer_score, rationale) VALUES
    -- Initiative 1: Knowledge Management Platform
    (1, 'CLARITY_MATURITY',  3, 3, 'Scope and objectives of the MVP are clearly defined and validated with stakeholders.'),
    (1, 'SUPPORT_OBJECTIVE', 3, 3, 'Requires an operational solution adopted across the organization for real daily use.'),
    (1, 'COMPLEXITY',        3, 3, 'High; requires architecture, GenAI integration and significant changes to how teams document.'),
    (1, 'DATA_INTEGRATIONS', 3, 2, 'Integrates with internal sources and may handle sensitive institutional knowledge.'),
    (1, 'RISK_IMPACT',       2, 2, 'Medium risk; wrong or stale answers could mislead, requires validation before broad rollout.'),
    (1, 'SUSTAINABILITY',    3, 3, 'Continuous use; needs ownership, curation and evolution over time.'),

    -- Initiative 2: Centralized Knowledge Base
    (2, 'CLARITY_MATURITY',  3, 3, 'Well-understood need; a documentation repository with clear requirements.'),
    (2, 'SUPPORT_OBJECTIVE', 3, 3, 'Operational repository used by all teams.'),
    (2, 'COMPLEXITY',        2, 2, 'Medium; mostly standard CRUD, taxonomy and search.'),
    (2, 'DATA_INTEGRATIONS', 2, 2, 'Uses internal content but not critical real-time integrations.'),
    (2, 'RISK_IMPACT',       1, 1, 'Low risk; documentation errors are correctable.'),
    (2, 'SUSTAINABILITY',    3, 3, 'Continuous use; requires curation discipline.'),

    -- Initiative 3: Knowledge Assistant (RAG)
    (3, 'CLARITY_MATURITY',  2, 2, 'Partially defined; retrieval quality criteria still being validated.'),
    (3, 'SUPPORT_OBJECTIVE', 2, 3, 'Validates an idea via prototype before becoming operational.'),
    (3, 'COMPLEXITY',        3, 3, 'High; RAG pipeline, embeddings and evaluation harness.'),
    (3, 'DATA_INTEGRATIONS', 3, 3, 'Uses real internal data and integrates with the knowledge base and LLM APIs.'),
    (3, 'RISK_IMPACT',       3, 2, 'High risk; hallucinations could affect decisions if not grounded and cited.'),
    (3, 'SUSTAINABILITY',    2, 2, 'Recurring use, still under evaluation.'),

    -- Initiative 4: Onboarding Knowledge Hub
    (4, 'CLARITY_MATURITY',  2, NULL, NULL),
    (4, 'SUPPORT_OBJECTIVE', 1, NULL, NULL),
    (4, 'COMPLEXITY',        2, NULL, NULL),
    (4, 'DATA_INTEGRATIONS', 1, NULL, NULL),
    (4, 'RISK_IMPACT',       1, NULL, NULL),
    (4, 'SUSTAINABILITY',    2, NULL, NULL);

-- **********************************
-- ****** Table collaborations ******
-- **********************************

INSERT INTO collaborations (id, init, user_id, type, workflow_status, content, parent) VALUES
    (1, 1, 1,  'ACTIVATION', 'FINISHED', 'Initiative created to consolidate organizational knowledge into a single platform.', NULL),
    (2, 1, 0,  'DIAGNOSIS',  'ASSIGNED', NULL, NULL),
    (3, 1, 0,  'DIAGNOSIS',  'NOTIFIED', NULL, NULL),
    (4, 1, 0,  'DIAGNOSIS',  'FINISHED', 'Assessed scope, criteria and expected impact with stakeholders; prioritized as HIGH.', NULL),
    (5, 1, 1,  'ACCEPTANCE', 'ASSIGNED', NULL, NULL),
    (6, 1, 1,  'ACCEPTANCE', 'NOTIFIED', NULL, NULL),
    (7, 1, 1,  'ACCEPTANCE', 'FINISHED', 'Built a proof of concept for the RAG assistant over a sample of documented assets.', NULL),
    (8, 1, 1,  'DELIVERY',   'ASSIGNED', NULL, NULL),
    (9, 1, 1,  'DELIVERY',   'NOTIFIED', NULL, NULL),
    (10, 1, 1, 'DELIVERY',   'FINISHED', NULL, NULL),
    (11, 1, 7,  'QUESTION',  NULL, 'Will the assistant cite the original source for every answer?', NULL),
    (12, 1, 1,  'ANSWER',    NULL, 'Yes; every answer must ground its response and link back to the source asset.', 5),
    (13, 1, 10, 'COMMENT',   NULL, 'Capturing tacit knowledge from senior staff should be part of the rollout plan.', NULL);

SELECT setval(pg_get_serial_sequence('collaborations', 'id'), (SELECT MAX(id) FROM collaborations));

-- **********************************
-- ******* Table related_inits ******
-- **********************************

INSERT INTO related_inits (source, target, type, rationale) VALUES
    (1, 2, 'CONTAINS',   'The knowledge base is the foundational component of the platform.'),
    (1, 3, 'CONTAINS',   'The RAG assistant is delivered as part of the platform.'),
    (1, 4, 'CONTAINS',   'The onboarding hub is a consumer surface within the platform.'),
    (1, 5, 'CONTAINS',   'The community of practice feeds tacit knowledge into the platform.'),
    (3, 2, 'DEPENDS_ON', 'The assistant retrieves and cites content from the knowledge base.'),
    (4, 2, 'DEPENDS_ON', 'Onboarding paths are built from knowledge base content.');

-- **********************************
-- ******* Table favorite_inits *****
-- **********************************

INSERT INTO favorite_inits (user_id, init) VALUES
    (0, 1),
    (1, 1),
    (2, 1),
    (5, 3);

-- **********************************
-- ****** Table init_permissions ****
-- **********************************

INSERT INTO init_permissions (init, target_type, target_code, access_level) VALUES
    (1, 'TEAM',   'CORE', 'MANAGE'),
    (1, 'ROLE',   'TL',   'MANAGE'),
    (1, 'PUBLIC', 'ALL',    'VIEW'),
    (3, 'TEAM',   'LAB',  'MANAGE'),
    (3, 'USER',   '5',    'MANAGE');
