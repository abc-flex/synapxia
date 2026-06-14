-- ************************************************
-- ***** Collaboration seed (real roster) *********
-- ************************************************
-- Real teams, roles, users, assignments, dimensions and metrics extracted from
-- db/data/data-assign.js: 5 squads, 55 collaborators, their team/role assignments
-- and one GenAI adoption metric each. Runs after 32-collab-insert.sql (lexical order);
-- the roles insert uses ON CONFLICT so it coexists with 32 today and stays valid once
-- 33 becomes the canonical collab seed and replaces 32.

-- **********************************
-- ********** Table Roles ***********
-- **********************************
-- Full role set for the real roster. ON CONFLICT keeps this re-runnable and avoids
-- clashing with the shared roles (BACK, FRONT, QA) seeded by 32-collab-insert.sql
-- until that file is retired and 33 becomes the canonical collab seed.

INSERT INTO roles (code, name, description) VALUES
    ('BACK',      'Backend Developer',        'Responsible for server-side development, APIs, data access and integration with external services, ensuring performance, security and scalability.'),
    ('FRONT',     'Frontend Developer',       'Responsible for user interface implementation, client-side logic and interaction patterns, ensuring usability, accessibility and a consistent user experience.'),
    ('QA',        'QA Engineer',              'Responsible for designing and executing tests, validating quality criteria and helping prevent defects through automated and manual testing practices.'),
    ('TM',        'Team Manager',             'Responsible for leading a delivery squad, coordinating its members, removing blockers and ensuring the team meets its objectives and commitments.'),
    ('TECH_LEAD', 'Technical Lead',           'Responsible for the technical direction across squads, defining reference architecture, standards and best practices, and mentoring developers.'),
    ('ARCH',      'Solution Architect',       'Responsible for designing solution and software architecture, ensuring technical coherence, scalability and alignment with enterprise standards.'),
    ('CTO',       'Chief Technology Officer', 'Responsible for the overall technology strategy and vision, leading innovation and aligning technical capabilities with business goals.'),
    ('CONS',      'Consultant',               'Specialized advisor who provides guidance, best practices and expertise to support the adoption of GenAI tools and methodologies.'),
    ('AUTO',      'Automation Engineer',      'Responsible for designing and implementing automation solutions for testing, deployment and operational workflows.'),
    ('QAM',       'QA Manager',               'Responsible for leading the quality assurance practice, defining the testing strategy and overseeing quality across teams and deliverables.'),
    ('PLAT',      'Platform Engineer',        'Responsible for building and maintaining the internal platforms, tooling and infrastructure that enable development teams.'),
    ('DEVOPS',    'DevOps Engineer',          'Responsible for CI/CD pipelines, infrastructure automation and operational reliability, bridging development and operations.')
ON CONFLICT (code) DO NOTHING;

-- **********************************
-- ********** Table Teams ***********
-- **********************************

INSERT INTO teams (code, name, description)
VALUES
    ('HADES',  'Hades',    'Cross-functional development squad covering backend, frontend and QA, responsible for delivering and evolving its assigned products.'),
    ('SKYNET', 'A-Skynet', 'Cross-functional development squad covering backend, frontend and QA, responsible for delivering and evolving its assigned products.'),
    ('KEPLER', 'B-Kepler', 'Cross-functional development squad covering backend, frontend and QA, responsible for delivering and evolving its assigned products.'),
    ('PIXEL',  'C-Pixel',  'Cross-functional development squad covering backend, frontend and QA, responsible for delivering and evolving its assigned products.'),
    ('ROCKET', 'E-Rocket', 'Cross-functional development squad covering backend, frontend and QA, responsible for delivering and evolving its assigned products.');

-- **********************************
-- ********** Table Users ***********
-- **********************************
-- Usernames are the email local-part; ids are auto-generated (do not assume a range).

WITH default_hash AS (
    SELECT '$2b$12$Q/ZWUi06lisvmpto32xbm.5r.ynn8fDfJ1fnLEPoBQqX.BqFAL5tG'::text AS h
    -- Password: Admin123! (bcrypt hash, cost=12)
),
user_data AS (
    SELECT *
    FROM (VALUES
        -- Hades
        ('rroldanb',      'rroldanb@ultragroupla.com',      'Roger Ricardo',    'Roldan Bonilla'),
        ('cgomezf',       'cgomezf@ultragroupla.com',       'Cristian',         'Gomez Florez'),
        ('jdurangor',     'jdurangor@ultragroupla.com',     'Jhonatan Alberto', 'Durango Rios'),
        ('kcharrasquield','kcharrasquield@ultragroupla.com','Kevin Andres',     'Charrasquiel Daza'),
        ('jceballoso',    'jceballoso@ultragroupla.com',    'Juan David',       'Ceballos Ospina'),
        ('oalzatef',      'oalzatef@ultragroupla.com',      'Oswaldo',          'Alzate Franco'),
        ('aemejia',       'aemejia@ultragroupla.com',       'Andrea Estefania', 'Mejia'),

        -- A-Skynet
        ('cfbenavidest',  'cfbenavidest@ultragroupla.com',  'Cristian Felipe',  'Benavides Troyano'),
        ('acarmonas',     'acarmonas@ultragroupla.com',     'Alber Joanny',     'Carmona Salazar'),
        ('jalvareze',     'jalvareze@ultragroupla.com',     'Juan Esteban',     'Alvarez Echavarria'),
        ('anietot',       'anietot@ultragroupla.com',       'Angelo',           'Nieto Triana'),
        ('lpuertar',      'lpuertar@ultragroupla.com',      'Luddy Mileny',     'Puerta Ruiz'),
        ('rjaramilloa',   'rjaramilloa@ultragroupla.com',   'Ricardo Enrique',  'Jaramillo Acevedo'),
        ('spimienton',    'spimienton@ultragroupla.com',    'Sergio Mauricio',  'Pimiento Niño'),
        ('crubiog',       'crubiog@ultragroupla.com',       'Carlos Alberto',   'Rubio Gallego'),
        ('jmflorezh',     'jmflorezh@ultragroupla.com',     'Jenny Marcela',    'Florez Hinestroza'),
        ('ngallegor',     'ngallegor@ultragroupla.com',     'Natalia',          'Gallego Rios'),

        -- B-Kepler
        ('ojbuitragoc',   'ojbuitragoc@ultragroupla.com',   'Oscar Julian',     'Buitrago Castro'),
        ('jcgonzalezs',   'jcgonzalezs@ultragroupla.com',   'Juan Carlos',      'Gonzalez Sanchez'),
        ('fzapatam',      'fzapatam@ultragroupla.com',      'Fernando',         'Zapata Montes'),
        ('sarianoa',      'sarianoa@ultragroupla.com',      'Sergio Alejandro', 'Riaño Acosta'),
        ('vpradan',       'vpradan@ultragroupla.com',       'Victor Alejandro', 'Prada Noreña'),
        ('cvelezt',       'cvelezt@ultragroupla.com',       'Cristhian David',  'Velez Torres'),
        ('jbarbosac',     'jbarbosac@ultragroupla.com',     'Jose Eulises',     'Barbosa Colorado'),
        ('jemarinh',      'jemarinh@ultragroupla.com',      'Jesus Ernesto',    'Marin Hernandez'),
        ('jromeroa',      'jromeroa@ultragroupla.com',      'Jeferson Daniel',  'Romero Acosta'),

        -- C-Pixel
        ('smonsalvec',    'smonsalvec@ultragroupla.com',    'Santiago',         'Monsalve Calderon'),
        ('omoraleso',     'omoraleso@ultragroupla.com',     'Oscar David',      'Morales Ortiz'),
        ('cpradas',       'cpradas@ultragroupla.com',       'Cristian David',   'Prada Suarez'),
        ('clreyesl',      'clreyesl@ultragroupla.com',      'Cesar Luis',       'Reyes Lopez'),
        ('rbetancurm',    'rbetancurm@ultragroupla.com',    'Robinson',         'Betancur Marin'),
        ('fbolanosr',     'fbolanosr@ultragroupla.com',     'Andres Felipe',    'Bolaños Ramirez'),
        ('cpelaezr',      'cpelaezr@ultragroupla.com',      'Camilo',           'Pelaez Ramirez'),
        ('yurreat',       'yurreat@ultragroupla.com',       'Yhonatan',         'Urrea Tascon'),
        ('afsanchezq',    'afsanchezq@ultragroupla.com',    'Andres Felipe',    'Sanchez Quevedo'),

        -- E-Rocket
        ('cgarzons',      'cgarzons@ultragroupla.com',      'Cristian',         'Garzon Sanchez'),
        ('yguerreroc',    'yguerreroc@ultragroupla.com',    'Yeferson Yuberley','Guerrero Castro'),
        ('jtapiash',      'jtapiash@ultragroupla.com',      'Jorge Eliecer',    'Tapias Higuita'),
        ('hrumbon',       'hrumbon@ultragroupla.com',       'Hernando Jose',    'Rumbo Nunez'),
        ('cespinosar',    'cespinosar@ultragroupla.com',    'Maria Camila',     'Espinosa Ramirez'),
        ('jospinal',      'jospinal@ultragroupla.com',      'Jeyson Julian',    'Ospina Leon'),
        ('jhidalgos',     'jhidalgos@ultragroupla.com',     'Johan Sebastian',  'Hidalgo Sandoval'),
        ('dcastellanosv', 'dcastellanosv@ultragroupla.com', 'Diego Fernando',   'Castellanos Vargas'),
        ('jceballosc',    'jceballosc@ultragroupla.com',    'Juan David',       'Ceballos Cogollo'),
        ('egonzalezs',    'egonzalezs@ultragroupla.com',    'Enma Del Carmen',  'Gonzalez Sanchez'),

        -- Cross-cutting roles (no team)
        ('jcestradau',    'jcestradau@ultragroupla.com',    'Juan Camilo',      'Estrada Uran'),
        ('vmastudillod',  'vmastudillod@ultragroupla.com',  'Victor Manuel',    'Astudillo'),
        ('eanchicos',     'eanchicos@ultragroupla.com',     'Edier',            'Anchico Silva'),
        ('aayalac',       'aayalac@ultragroupla.com',       'Andres Mauricio',  'Ayala Cardona'),
        ('spatinob',      'spatinob@ultragroupla.com',      'Santiago',         'Patiño Betancur'),
        ('jquintero',     'jquintero@ultragroupla.com',     'Juan Bernardo',    'Quintero'),
        ('dacardonac',    'dacardonac@ultragroupla.com',    'Daniela Alexandra','Cardona Castaño'),
        ('kjimenezp',     'kjimenezp@ultragroupla.com',     'Karen Stefany',    'Jiménez Pérez'),
        ('waguilarc',     'waguilarc@ultragroupla.com',     'Wilmar',           'Aguilar Castro'),
        ('scolpasg',      'scolpasg@ultragroupla.com',      'Samir Eduardo',    'Colpas Gonzalez')
    ) AS v(username, email, first_name, last_name)
)
INSERT INTO users (
    username,
    email,
    password_hash,
    first_name,
    last_name,
    profile,
    unit,
    is_active
)
SELECT
    username,
    email,
    (SELECT h FROM default_hash),
    first_name,
    last_name,
    'COLLABORATOR',
    'ENG',
    TRUE
FROM user_data;

-- Keep the identity sequence aligned with the rows inserted above
SELECT setval(pg_get_serial_sequence('users', 'id'), (SELECT MAX(id) FROM users));

-- **********************************
-- ******* Table Assignments ********
-- **********************************
-- Linked by email so the assignment lands on the right user regardless of the
-- auto-generated id. team = NULL for cross-cutting roles without a squad.

INSERT INTO assignments (team, user_id, role)
SELECT a.team, u.id, a.role
FROM (VALUES
    -- Hades
    ('rroldanb@ultragroupla.com',      'HADES',  'BACK'),
    ('cgomezf@ultragroupla.com',       'HADES',  'FRONT'),
    ('jdurangor@ultragroupla.com',     'HADES',  'FRONT'),
    ('kcharrasquield@ultragroupla.com','HADES',  'FRONT'),
    ('jceballoso@ultragroupla.com',    'HADES',  'QA'),
    ('oalzatef@ultragroupla.com',      'HADES',  'QA'),
    ('aemejia@ultragroupla.com',       'HADES',  'QA'),

    -- A-Skynet
    ('cfbenavidest@ultragroupla.com',  'SKYNET', 'TM'),
    ('acarmonas@ultragroupla.com',     'SKYNET', 'BACK'),
    ('jalvareze@ultragroupla.com',     'SKYNET', 'BACK'),
    ('anietot@ultragroupla.com',       'SKYNET', 'BACK'),
    ('lpuertar@ultragroupla.com',      'SKYNET', 'FRONT'),
    ('rjaramilloa@ultragroupla.com',   'SKYNET', 'FRONT'),
    ('spimienton@ultragroupla.com',    'SKYNET', 'FRONT'),
    ('crubiog@ultragroupla.com',       'SKYNET', 'QA'),
    ('jmflorezh@ultragroupla.com',     'SKYNET', 'QA'),
    ('ngallegor@ultragroupla.com',     'SKYNET', 'QA'),

    -- B-Kepler
    ('ojbuitragoc@ultragroupla.com',   'KEPLER', 'TM'),
    ('jcgonzalezs@ultragroupla.com',   'KEPLER', 'BACK'),
    ('fzapatam@ultragroupla.com',      'KEPLER', 'BACK'),
    ('sarianoa@ultragroupla.com',      'KEPLER', 'FRONT'),
    ('vpradan@ultragroupla.com',       'KEPLER', 'FRONT'),
    ('cvelezt@ultragroupla.com',       'KEPLER', 'FRONT'),
    ('jbarbosac@ultragroupla.com',     'KEPLER', 'QA'),
    ('jemarinh@ultragroupla.com',      'KEPLER', 'QA'),
    ('jromeroa@ultragroupla.com',      'KEPLER', 'QA'),

    -- C-Pixel
    ('smonsalvec@ultragroupla.com',    'PIXEL',  'TM'),
    ('omoraleso@ultragroupla.com',     'PIXEL',  'BACK'),
    ('cpradas@ultragroupla.com',       'PIXEL',  'BACK'),
    ('clreyesl@ultragroupla.com',      'PIXEL',  'BACK'),
    ('rbetancurm@ultragroupla.com',    'PIXEL',  'FRONT'),
    ('fbolanosr@ultragroupla.com',     'PIXEL',  'FRONT'),
    ('cpelaezr@ultragroupla.com',      'PIXEL',  'QA'),
    ('yurreat@ultragroupla.com',       'PIXEL',  'QA'),
    ('afsanchezq@ultragroupla.com',    'PIXEL',  'QA'),

    -- E-Rocket
    ('cgarzons@ultragroupla.com',      'ROCKET', 'TM'),
    ('yguerreroc@ultragroupla.com',    'ROCKET', 'BACK'),
    ('jtapiash@ultragroupla.com',      'ROCKET', 'BACK'),
    ('hrumbon@ultragroupla.com',       'ROCKET', 'BACK'),
    ('cespinosar@ultragroupla.com',    'ROCKET', 'FRONT'),
    ('jospinal@ultragroupla.com',      'ROCKET', 'FRONT'),
    ('jhidalgos@ultragroupla.com',     'ROCKET', 'FRONT'),
    ('dcastellanosv@ultragroupla.com', 'ROCKET', 'QA'),
    ('jceballosc@ultragroupla.com',    'ROCKET', 'QA'),
    ('egonzalezs@ultragroupla.com',    'ROCKET', 'QA'),

    -- Cross-cutting roles (no team)
    ('jcestradau@ultragroupla.com',    NULL,     'TECH_LEAD'),
    ('vmastudillod@ultragroupla.com',  NULL,     'TECH_LEAD'),
    ('eanchicos@ultragroupla.com',     NULL,     'TECH_LEAD'),
    ('aayalac@ultragroupla.com',       NULL,     'ARCH'),
    ('spatinob@ultragroupla.com',      NULL,     'CTO'),
    ('jquintero@ultragroupla.com',     NULL,     'CONS'),
    ('dacardonac@ultragroupla.com',    NULL,     'AUTO'),
    ('kjimenezp@ultragroupla.com',     NULL,     'QAM'),
    ('waguilarc@ultragroupla.com',     NULL,     'PLAT'),
    ('scolpasg@ultragroupla.com',      NULL,     'DEVOPS')
) AS a(email, team, role)
JOIN users u ON u.email = a.email;

-- **********************************
-- ******** Table Dimensions ********
-- **********************************
-- Two GenAI adoption axes. Each references the matching SCALE list defined in
-- 31-collab-ddl.sql (NO_USAGE → VERY_HIGH). Unit is left NULL: these are qualitative
-- scales, not a counted magnitude.

INSERT INTO dimensions (code, name, description, scale, unit) VALUES
    ('GENAI_DEV_ADOPTION', 'GenAI Adoption for Devs',
     'Level of adoption of Generative AI tools and practices among development-oriented roles (backend, frontend, leads, architecture, platform and operations).',
     'GENAI_DEV_ADOPTION', NULL),
    ('GENAI_QA_ADOPTION', 'GenAI Adoption for QA',
     'Level of adoption of Generative AI tools and practices among QA and quality-oriented roles.',
     'GENAI_QA_ADOPTION', NULL);

-- **********************************
-- ********** Table Metrics *********
-- **********************************
-- One adoption measurement per collaborator (measured 2025-12-19). The dimension is
-- chosen by role: QA / QA Manager / Automation Engineer are scored on GENAI_QA_ADOPTION,
-- everyone else on GENAI_DEV_ADOPTION. Linked by email so each metric lands on the
-- right assignment regardless of auto-generated ids. UNDEFINED = not yet measured.

INSERT INTO metrics (dimension, assignment, value, observation, measured_at)
SELECT m.dimension, a.id, m.value, m.observation, TIMESTAMPTZ '2025-12-19'
FROM (VALUES
    -- Hades
    ('rroldanb@ultragroupla.com',      'GENAI_DEV_ADOPTION', 'MODERATE',  NULL),
    ('cgomezf@ultragroupla.com',       'GENAI_DEV_ADOPTION', 'MODERATE',  NULL),
    ('jdurangor@ultragroupla.com',     'GENAI_DEV_ADOPTION', 'MODERATE',  'Problemas para la configuración del MCP de Azure DevOps'),
    ('kcharrasquield@ultragroupla.com','GENAI_DEV_ADOPTION', 'MODERATE',  NULL),
    ('jceballoso@ultragroupla.com',    'GENAI_QA_ADOPTION',  'LOW',       'Problemas para la configuración del MCP de Azure DevOps'),
    ('oalzatef@ultragroupla.com',      'GENAI_QA_ADOPTION',  'LOW',       'Configuración del MCP de Azure DevOps'),
    ('aemejia@ultragroupla.com',       'GENAI_QA_ADOPTION',  'NO_USAGE',  NULL),

    -- A-Skynet
    ('cfbenavidest@ultragroupla.com',  'GENAI_DEV_ADOPTION', 'MODERATE',  E'Configuración del MCP de Azure DevOps\nPrompts interesantes para varios frentes'),
    ('acarmonas@ultragroupla.com',     'GENAI_DEV_ADOPTION', 'MODERATE',  'Configuración del MCP de Azure DevOps'),
    ('jalvareze@ultragroupla.com',     'GENAI_DEV_ADOPTION', 'HIGH',      'Revisar definición de contexto para evitar workslop'),
    ('anietot@ultragroupla.com',       'GENAI_DEV_ADOPTION', 'MODERATE',  'Revisar definición de contexto para evitar workslop'),
    ('lpuertar@ultragroupla.com',      'GENAI_DEV_ADOPTION', 'HIGH',      'Actualmente configurado y usando el MCP de Figma'),
    ('rjaramilloa@ultragroupla.com',   'GENAI_DEV_ADOPTION', 'MODERATE',  'Configuración del MCP de Azure DevOps'),
    ('spimienton@ultragroupla.com',    'GENAI_DEV_ADOPTION', 'UNDEFINED', NULL),
    ('crubiog@ultragroupla.com',       'GENAI_QA_ADOPTION',  'LOW',       'Configuración del MCP de Azure DevOps'),
    ('jmflorezh@ultragroupla.com',     'GENAI_QA_ADOPTION',  'NO_USAGE',  NULL),
    ('ngallegor@ultragroupla.com',     'GENAI_QA_ADOPTION',  'NO_USAGE',  NULL),

    -- B-Kepler
    ('ojbuitragoc@ultragroupla.com',   'GENAI_DEV_ADOPTION', 'HIGH',      'Prompt para dividir HU y revisión de código'),
    ('jcgonzalezs@ultragroupla.com',   'GENAI_DEV_ADOPTION', 'HIGH',      'Prompt para migración de SOAP a REST'),
    ('fzapatam@ultragroupla.com',      'GENAI_DEV_ADOPTION', 'HIGH',      E'Revisar definición de contexto para evitar workslop\nPrompts para sincronizar sprints y revisión de PR'),
    ('sarianoa@ultragroupla.com',      'GENAI_DEV_ADOPTION', 'UNDEFINED', NULL),
    ('vpradan@ultragroupla.com',       'GENAI_DEV_ADOPTION', 'HIGH',      'Revisar definición de contexto para evitar workslop'),
    ('cvelezt@ultragroupla.com',       'GENAI_DEV_ADOPTION', 'HIGH',      NULL),
    ('jbarbosac@ultragroupla.com',     'GENAI_QA_ADOPTION',  'HIGH',      'Piloto de Multi-Agente en QA'),
    ('jemarinh@ultragroupla.com',      'GENAI_QA_ADOPTION',  'HIGH',      'Prompts interesantes para varios frentes'),
    ('jromeroa@ultragroupla.com',      'GENAI_QA_ADOPTION',  'VERY_HIGH', NULL),

    -- C-Pixel
    ('smonsalvec@ultragroupla.com',    'GENAI_DEV_ADOPTION', 'VERY_HIGH', E'Uso de Copilot en 365 y modo plan en VSCode\nAspectos de arquitectura de referencia y documentación\nIngeniero de prompts (revisión y creador de prompts)\nPrompt de creador y revisor de HU y TC\nAgente asistentes de reuniones y proyecto de agente estimador'),
    ('omoraleso@ultragroupla.com',     'GENAI_DEV_ADOPTION', 'HIGH',      NULL),
    ('cpradas@ultragroupla.com',       'GENAI_DEV_ADOPTION', 'HIGH',      'Prompt de agregar proveedores'),
    ('clreyesl@ultragroupla.com',      'GENAI_DEV_ADOPTION', 'UNDEFINED', NULL),
    ('rbetancurm@ultragroupla.com',    'GENAI_DEV_ADOPTION', 'HIGH',      'Prompts interesantes para varios frentes'),
    ('fbolanosr@ultragroupla.com',     'GENAI_DEV_ADOPTION', 'HIGH',      NULL),
    ('cpelaezr@ultragroupla.com',      'GENAI_QA_ADOPTION',  'HIGH',      'Tokens agotados'),
    ('yurreat@ultragroupla.com',       'GENAI_QA_ADOPTION',  'NO_USAGE',  NULL),
    ('afsanchezq@ultragroupla.com',    'GENAI_QA_ADOPTION',  'NO_USAGE',  NULL),

    -- E-Rocket
    ('cgarzons@ultragroupla.com',      'GENAI_DEV_ADOPTION', 'HIGH',      NULL),
    ('yguerreroc@ultragroupla.com',    'GENAI_DEV_ADOPTION', 'VERY_HIGH', NULL),
    ('jtapiash@ultragroupla.com',      'GENAI_DEV_ADOPTION', 'MODERATE',  'Problemas para la configuración del MCP de Azure DevOps'),
    ('hrumbon@ultragroupla.com',       'GENAI_DEV_ADOPTION', 'VERY_HIGH', NULL),
    ('cespinosar@ultragroupla.com',    'GENAI_DEV_ADOPTION', 'HIGH',      NULL),
    ('jospinal@ultragroupla.com',      'GENAI_DEV_ADOPTION', 'HIGH',      'Prompt para GitFlow'),
    ('jhidalgos@ultragroupla.com',     'GENAI_DEV_ADOPTION', 'HIGH',      E'Revisar definición de contexto para evitar workslop\nPrompt de revisión de logs'),
    ('dcastellanosv@ultragroupla.com', 'GENAI_QA_ADOPTION',  'NO_USAGE',  NULL),
    ('jceballosc@ultragroupla.com',    'GENAI_QA_ADOPTION',  'HIGH',      NULL),
    ('egonzalezs@ultragroupla.com',    'GENAI_QA_ADOPTION',  'MODERATE',  NULL),

    -- Cross-cutting roles (no team)
    ('jcestradau@ultragroupla.com',    'GENAI_DEV_ADOPTION', 'LOW',       'Configuración del MCP de Azure DevOps'),
    ('vmastudillod@ultragroupla.com',  'GENAI_DEV_ADOPTION', 'HIGH',      'Prompts para la arquitectura de referencia'),
    ('eanchicos@ultragroupla.com',     'GENAI_DEV_ADOPTION', 'HIGH',      NULL),
    ('aayalac@ultragroupla.com',       'GENAI_DEV_ADOPTION', 'UNDEFINED', NULL),
    ('spatinob@ultragroupla.com',      'GENAI_DEV_ADOPTION', 'UNDEFINED', NULL),
    ('jquintero@ultragroupla.com',     'GENAI_DEV_ADOPTION', 'VERY_HIGH', NULL),
    ('dacardonac@ultragroupla.com',    'GENAI_QA_ADOPTION',  'HIGH',      'Problemas para la Configuración del MCP de Azure DevOps'),
    ('kjimenezp@ultragroupla.com',     'GENAI_QA_ADOPTION',  'MODERATE',  'Problemas para la Configuración del MCP de Azure DevOps'),
    ('waguilarc@ultragroupla.com',     'GENAI_DEV_ADOPTION', 'UNDEFINED', NULL),
    ('scolpasg@ultragroupla.com',      'GENAI_DEV_ADOPTION', 'UNDEFINED', NULL)
) AS m(email, dimension, value, observation)
JOIN users u ON u.email = m.email
JOIN assignments a ON a.user_id = u.id;
