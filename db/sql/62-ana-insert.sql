 -- **********************************
-- ******** Table dashboards ********
-- **********************************
-- Three analytics dashboards measuring Generative AI adoption:
--   1. by the development team as a whole,
--   2. broken down by role,
--   3. broken down by team.
-- type / sources_types / status reference the DASHBOARD_TYPE / SOURCE_TYPE /
-- DASHBOARD_STATUS lists defined in 61-ana-ddl.sql.

INSERT INTO dashboards (id, name, description, type, sources_types, source_url, status, tags, detail) VALUES
    (1, 'GenAI Adoption — Development Team',
     'Overall view of Generative AI adoption across the whole development team: active users, assets in use, and usage trends over time.',
     'DASHBOARD', 'POWER_BI', 'https://app.powerbi.com/view?r=synapxia-genai-adoption-team',
     'PUBLISHED', '["genai", "adoption", "development", "overview"]',
     $$# GenAI Adoption — Development Team

## Purpose
Single, organization-wide picture of how the development team is adopting
Generative AI assets (prompts, agents, MCPs, RAG apps).

## Key metrics
- Active GenAI users vs. total developers (adoption rate %).
- Number of GenAI assets in use and their usage volume.
- Weekly active users and usage trend (last 12 weeks).
- Top adopted assets across the whole team.

## Audience
Engineering leadership and the GenAI enablement team.
$$),
    (2, 'GenAI Adoption — by Role',
     'Generative AI adoption broken down by role (BACK, FRONT, QA, PO, TL) to compare how each role leverages GenAI assets.',
     'ANALYTICAL_VIEW', 'POWER_BI', 'https://app.powerbi.com/view?r=synapxia-genai-adoption-role',
     'PUBLISHED', '["genai", "adoption", "role", "comparison"]',
     $$# GenAI Adoption — by Role

## Purpose
Compare Generative AI adoption across roles to spot where enablement effort
should focus.

## Key metrics
- Adoption rate per role (active GenAI users / users in role).
- Average usage events per user, per role.
- Most-used asset category per role (prompts, agents, MCPs).
- Role-over-role trend over the selected period.

## Audience
Team leads and role chapter leads.
$$),
    (3, 'GenAI Adoption — by Team',
     'Generative AI adoption broken down by team (CORE, SUPPORT, OPS, ANALYTICS, LAB) to compare adoption maturity across squads.',
     'DASHBOARD', 'LOOKER_STUDIO', 'https://lookerstudio.google.com/embed/reporting/synapxia-genai-adoption-team-breakdown',
     'PUBLISHED', '["genai", "adoption", "team", "comparison"]',
     $$# GenAI Adoption — by Team

## Purpose
Compare Generative AI adoption maturity across the five squads to identify
leaders and laggards and to share best practices.

## Key metrics
- Adoption rate per team (active GenAI users / team members).
- Usage volume per team and per active user.
- Asset contributions vs. consumption ratio per team.
- Team ranking and trend over the selected period.

## Audience
Engineering leadership and team leads.
$$);

-- Keep the identity sequence aligned with the explicit ids above
SELECT setval(pg_get_serial_sequence('dashboards', 'id'), (SELECT MAX(id) FROM dashboards));

-- **********************************
-- ******** Table parameters ********
-- **********************************
-- Runtime filters for each dashboard. data_type references PARAM_TYPE.
-- `list` is NULL for free selectors backed by tables (role/team) and for
-- date ranges; context_binding is left NULL (no permission-scoped binding).

INSERT INTO parameters (dashboard, name, label, data_type, default_value, is_required, list) VALUES
    -- Dashboard 1: Development Team (overall)
    (1, 'date_from',   'From date',     'DATE',    '2026-01-01', TRUE,  NULL),
    (1, 'date_to',     'To date',       'DATE',    '2026-06-30', TRUE,  NULL),
    (1, 'granularity', 'Granularity',   'STRING',  'WEEK',       FALSE, NULL),
    (1, 'min_events',  'Min. events',   'NUMBER',  '1',          FALSE, NULL),

    -- Dashboard 2: by Role
    (2, 'date_from',   'From date',     'DATE',    '2026-01-01', TRUE,  NULL),
    (2, 'date_to',     'To date',       'DATE',    '2026-06-30', TRUE,  NULL),
    (2, 'role',        'Role',          'STRING',  NULL,         FALSE, NULL),
    (2, 'granularity', 'Granularity',   'STRING',  'MONTH',      FALSE, NULL),

    -- Dashboard 3: by Team
    (3, 'date_from',   'From date',     'DATE',    '2026-01-01', TRUE,  NULL),
    (3, 'date_to',     'To date',       'DATE',    '2026-06-30', TRUE,  NULL),
    (3, 'team',        'Team',          'STRING',  NULL,         FALSE, NULL),
    (3, 'granularity', 'Granularity',   'STRING',  'MONTH',      FALSE, NULL);

-- **********************************
-- ******** Table executions ********
-- **********************************
-- Sample execution log. status references EXECUTION_STATUS; payload captures
-- the parameter values used for the run.

INSERT INTO executions (id, dashboard, user_id, payload, status, error_message, duration_ms) VALUES
    (1, 1, 0,  '{"date_from": "2026-01-01", "date_to": "2026-06-30", "granularity": "WEEK"}',  'SUCCESS', NULL, 842),
    (2, 1, 37, '{"date_from": "2026-04-01", "date_to": "2026-06-30", "granularity": "WEEK"}',  'SUCCESS', NULL, 765),
    (3, 2, 38, '{"date_from": "2026-01-01", "date_to": "2026-06-30", "role": "BACK"}',         'SUCCESS', NULL, 612),
    (4, 2, 1,  '{"date_from": "2026-01-01", "date_to": "2026-06-30", "role": "FRONT"}',        'SUCCESS', NULL, 689),
    (5, 3, 0,  '{"date_from": "2026-01-01", "date_to": "2026-06-30", "team": "CORE"}',         'SUCCESS', NULL, 904),
    (6, 3, 40, '{"date_from": "2026-01-01", "date_to": "2026-06-30", "team": "LAB"}',          'TIMEOUT', 'Source query exceeded the 30s limit.', 30000);

-- Keep the identity sequence aligned with the explicit ids above
SELECT setval(pg_get_serial_sequence('executions', 'id'), (SELECT MAX(id) FROM executions));

-- **********************************
-- ***** Table favorite_dashboards **
-- **********************************

INSERT INTO favorite_dashboards (user_id, dashboard) VALUES
    (0,  1),
    (1,  1),
    (37, 2),
    (37, 3);

-- **********************************
-- **** Table dashboard_permissions *
-- **********************************
-- target_type / access_level reference the shared TARGET_TYPE / ACCESS_LEVEL lists.

INSERT INTO dashboard_permissions (dashboard, target_type, target_code, access_level) VALUES
    (1, 'PUBLIC', 'ALL',       'VIEW'),
    (1, 'ROLE',   'TL',        'MANAGE'),
    (2, 'ROLE',   'TL',        'VIEW'),
    (2, 'TEAM',   'ANALYTICS', 'MANAGE'),
    (3, 'PUBLIC', 'ALL',       'VIEW'),
    (3, 'TEAM',   'ANALYTICS', 'MANAGE');
