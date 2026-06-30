-- **********************************
-- ********** Table Roles ***********
-- **********************************

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
-- Codenames anonymized (HADES/SKYNET/KEPLER/PIXEL/ROCKET → ALPHA..ECHO).

INSERT INTO teams (code, name, description)
VALUES
    ('ALPHA',   'Team Alpha',   'Cross-functional development squad covering backend, frontend and QA, responsible for delivering and evolving its assigned products.'),
    ('BRAVO',   'Team Bravo',   'Cross-functional development squad covering backend, frontend and QA, responsible for delivering and evolving its assigned products.'),
    ('CHARLIE', 'Team Charlie', 'Cross-functional development squad covering backend, frontend and QA, responsible for delivering and evolving its assigned products.'),
    ('DELTA',   'Team Delta',   'Cross-functional development squad covering backend, frontend and QA, responsible for delivering and evolving its assigned products.'),
    ('ECHO',    'Team Echo',    'Cross-functional development squad covering backend, frontend and QA, responsible for delivering and evolving its assigned products.');

-- **********************************
-- ********** Table Users ***********
-- **********************************

WITH default_hash AS (
    SELECT '$2b$12$Q/ZWUi06lisvmpto32xbm.5r.ynn8fDfJ1fnLEPoBQqX.BqFAL5tG'::text AS h
    -- Password: Admin123! (bcrypt hash, cost=12)
),
user_data AS (
    SELECT *
    FROM (VALUES
        -- Team Alpha
        ('mateo.restrepo',    'mateo.restrepo@abcflex.com.co',    'Mateo',       'Restrepo'),
        ('valentina.ortiz',   'valentina.ortiz@abcflex.com.co',   'Valentina',   'Ortiz'),
        ('santiago.marin',    'santiago.marin@abcflex.com.co',    'Santiago',    'Marin'),
        ('camila.rojas',      'camila.rojas@abcflex.com.co',      'Camila',      'Rojas'),
        ('daniela.castro',    'daniela.castro@abcflex.com.co',    'Daniela',     'Castro'),
        ('andres.pena',       'andres.pena@abcflex.com.co',       'Andres',      'Pena'),
        ('laura.gimenez',     'laura.gimenez@abcflex.com.co',     'Laura',       'Gimenez'),

        -- Team Bravo
        ('felipe.cardenas',   'felipe.cardenas@abcflex.com.co',   'Felipe',      'Cardenas'),
        ('sofia.morales',     'sofia.morales@abcflex.com.co',     'Sofia',       'Morales'),
        ('juan.herrera',      'juan.herrera@abcflex.com.co',      'Juan',        'Herrera'),
        ('sebastian.lopez',   'sebastian.lopez@abcflex.com.co',   'Sebastian',   'Lopez'),
        ('isabella.vargas',   'isabella.vargas@abcflex.com.co',   'Isabella',    'Vargas'),
        ('nicolas.gomez',     'nicolas.gomez@abcflex.com.co',     'Nicolas',     'Gomez'),
        ('mariana.diaz',      'mariana.diaz@abcflex.com.co',      'Mariana',     'Diaz'),
        ('david.sanchez',     'david.sanchez@abcflex.com.co',     'David',       'Sanchez'),
        ('carolina.torres',   'carolina.torres@abcflex.com.co',   'Carolina',    'Torres'),
        ('diego.ramirez',     'diego.ramirez@abcflex.com.co',     'Diego',       'Ramirez'),

        -- Team Charlie
        ('alejandro.rios',    'alejandro.rios@abcflex.com.co',    'Alejandro',   'Rios'),
        ('manuela.suarez',    'manuela.suarez@abcflex.com.co',    'Manuela',     'Suarez'),
        ('tomas.beltran',     'tomas.beltran@abcflex.com.co',     'Tomas',       'Beltran'),
        ('gabriela.mendoza',  'gabriela.mendoza@abcflex.com.co',  'Gabriela',    'Mendoza'),
        ('samuel.acosta',     'samuel.acosta@abcflex.com.co',     'Samuel',      'Acosta'),
        ('antonia.navarro',   'antonia.navarro@abcflex.com.co',   'Antonia',     'Navarro'),
        ('emanuel.cortes',    'emanuel.cortes@abcflex.com.co',    'Emanuel',     'Cortes'),
        ('salome.guzman',     'salome.guzman@abcflex.com.co',     'Salome',      'Guzman'),
        ('martin.quintero',   'martin.quintero@abcflex.com.co',   'Martin',      'Quintero'),

        -- Team Delta
        ('lucas.forero',      'lucas.forero@abcflex.com.co',      'Lucas',       'Forero'),
        ('valeria.pardo',     'valeria.pardo@abcflex.com.co',     'Valeria',     'Pardo'),
        ('emiliano.salazar',  'emiliano.salazar@abcflex.com.co',  'Emiliano',    'Salazar'),
        ('renata.cabrera',    'renata.cabrera@abcflex.com.co',    'Renata',      'Cabrera'),
        ('joaquin.pineda',    'joaquin.pineda@abcflex.com.co',    'Joaquin',     'Pineda'),
        ('luciana.bermudez',  'luciana.bermudez@abcflex.com.co',  'Luciana',     'Bermudez'),
        ('maximiliano.duarte','maximiliano.duarte@abcflex.com.co','Maximiliano', 'Duarte'),
        ('sara.velasquez',    'sara.velasquez@abcflex.com.co',    'Sara',        'Velasquez'),
        ('daniel.carmona',    'daniel.carmona@abcflex.com.co',    'Daniel',      'Carmona'),

        -- Team Echo
        ('pablo.henao',       'pablo.henao@abcflex.com.co',       'Pablo',       'Henao'),
        ('antonella.cano',    'antonella.cano@abcflex.com.co',    'Antonella',   'Cano'),
        ('simon.arias',       'simon.arias@abcflex.com.co',       'Simon',       'Arias'),
        ('juliana.mora',      'juliana.mora@abcflex.com.co',      'Juliana',     'Mora'),
        ('esteban.ospina',    'esteban.ospina@abcflex.com.co',    'Esteban',     'Ospina'),
        ('catalina.franco',   'catalina.franco@abcflex.com.co',   'Catalina',    'Franco'),
        ('matias.rincon',     'matias.rincon@abcflex.com.co',     'Matias',      'Rincon'),
        ('paulina.galvis',    'paulina.galvis@abcflex.com.co',    'Paulina',     'Galvis'),
        ('ivan.montoya',      'ivan.montoya@abcflex.com.co',      'Ivan',        'Montoya'),
        ('natalia.cifuentes', 'natalia.cifuentes@abcflex.com.co', 'Natalia',     'Cifuentes'),

        -- Cross-cutting roles (no team)
        ('ricardo.bedoya',    'ricardo.bedoya@abcflex.com.co',    'Ricardo',     'Bedoya'),
        ('adriana.velez',     'adriana.velez@abcflex.com.co',     'Adriana',     'Velez'),
        ('oscar.patino',      'oscar.patino@abcflex.com.co',      'Oscar',       'Patino'),
        ('hernan.giraldo',    'hernan.giraldo@abcflex.com.co',    'Hernan',      'Giraldo'),
        ('patricia.londono',  'patricia.londono@abcflex.com.co',  'Patricia',    'Londono'),
        ('roberto.aguirre',   'roberto.aguirre@abcflex.com.co',   'Roberto',     'Aguirre'),
        ('lorena.bautista',   'lorena.bautista@abcflex.com.co',   'Lorena',      'Bautista'),
        ('carmen.salgado',    'carmen.salgado@abcflex.com.co',    'Carmen',      'Salgado'),
        ('wilmer.trujillo',   'wilmer.trujillo@abcflex.com.co',   'Wilmer',      'Trujillo'),
        ('sergio.pabon',      'sergio.pabon@abcflex.com.co',      'Sergio',      'Pabon')
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

INSERT INTO assignments (team, user_id, role)
SELECT a.team, u.id, a.role
FROM (VALUES
    -- Team Alpha
    ('mateo.restrepo@abcflex.com.co',    'ALPHA',   'BACK'),
    ('valentina.ortiz@abcflex.com.co',   'ALPHA',   'FRONT'),
    ('santiago.marin@abcflex.com.co',    'ALPHA',   'FRONT'),
    ('camila.rojas@abcflex.com.co',      'ALPHA',   'FRONT'),
    ('daniela.castro@abcflex.com.co',    'ALPHA',   'QA'),
    ('andres.pena@abcflex.com.co',       'ALPHA',   'QA'),
    ('laura.gimenez@abcflex.com.co',     'ALPHA',   'QA'),

    -- Team Bravo
    ('felipe.cardenas@abcflex.com.co',   'BRAVO',   'TM'),
    ('sofia.morales@abcflex.com.co',     'BRAVO',   'BACK'),
    ('juan.herrera@abcflex.com.co',      'BRAVO',   'BACK'),
    ('sebastian.lopez@abcflex.com.co',   'BRAVO',   'BACK'),
    ('isabella.vargas@abcflex.com.co',   'BRAVO',   'FRONT'),
    ('nicolas.gomez@abcflex.com.co',     'BRAVO',   'FRONT'),
    ('mariana.diaz@abcflex.com.co',      'BRAVO',   'FRONT'),
    ('david.sanchez@abcflex.com.co',     'BRAVO',   'QA'),
    ('carolina.torres@abcflex.com.co',   'BRAVO',   'QA'),
    ('diego.ramirez@abcflex.com.co',     'BRAVO',   'QA'),

    -- Team Charlie
    ('alejandro.rios@abcflex.com.co',    'CHARLIE', 'TM'),
    ('manuela.suarez@abcflex.com.co',    'CHARLIE', 'BACK'),
    ('tomas.beltran@abcflex.com.co',     'CHARLIE', 'BACK'),
    ('gabriela.mendoza@abcflex.com.co',  'CHARLIE', 'FRONT'),
    ('samuel.acosta@abcflex.com.co',     'CHARLIE', 'FRONT'),
    ('antonia.navarro@abcflex.com.co',   'CHARLIE', 'FRONT'),
    ('emanuel.cortes@abcflex.com.co',    'CHARLIE', 'QA'),
    ('salome.guzman@abcflex.com.co',     'CHARLIE', 'QA'),
    ('martin.quintero@abcflex.com.co',   'CHARLIE', 'QA'),

    -- Team Delta
    ('lucas.forero@abcflex.com.co',      'DELTA',   'TM'),
    ('valeria.pardo@abcflex.com.co',     'DELTA',   'BACK'),
    ('emiliano.salazar@abcflex.com.co',  'DELTA',   'BACK'),
    ('renata.cabrera@abcflex.com.co',    'DELTA',   'BACK'),
    ('joaquin.pineda@abcflex.com.co',    'DELTA',   'FRONT'),
    ('luciana.bermudez@abcflex.com.co',  'DELTA',   'FRONT'),
    ('maximiliano.duarte@abcflex.com.co','DELTA',   'QA'),
    ('sara.velasquez@abcflex.com.co',    'DELTA',   'QA'),
    ('daniel.carmona@abcflex.com.co',    'DELTA',   'QA'),

    -- Team Echo
    ('pablo.henao@abcflex.com.co',       'ECHO',    'TM'),
    ('antonella.cano@abcflex.com.co',    'ECHO',    'BACK'),
    ('simon.arias@abcflex.com.co',       'ECHO',    'BACK'),
    ('juliana.mora@abcflex.com.co',      'ECHO',    'BACK'),
    ('esteban.ospina@abcflex.com.co',    'ECHO',    'FRONT'),
    ('catalina.franco@abcflex.com.co',   'ECHO',    'FRONT'),
    ('matias.rincon@abcflex.com.co',     'ECHO',    'FRONT'),
    ('paulina.galvis@abcflex.com.co',    'ECHO',    'QA'),
    ('ivan.montoya@abcflex.com.co',      'ECHO',    'QA'),
    ('natalia.cifuentes@abcflex.com.co', 'ECHO',    'QA'),

    -- Cross-cutting roles (no team)
    ('ricardo.bedoya@abcflex.com.co',    NULL,      'TECH_LEAD'),
    ('adriana.velez@abcflex.com.co',     NULL,      'TECH_LEAD'),
    ('oscar.patino@abcflex.com.co',      NULL,      'TECH_LEAD'),
    ('hernan.giraldo@abcflex.com.co',    NULL,      'ARCH'),
    ('patricia.londono@abcflex.com.co',  NULL,      'CTO'),
    ('roberto.aguirre@abcflex.com.co',   NULL,      'CONS'),
    ('lorena.bautista@abcflex.com.co',   NULL,      'AUTO'),
    ('carmen.salgado@abcflex.com.co',    NULL,      'QAM'),
    ('wilmer.trujillo@abcflex.com.co',   NULL,      'PLAT'),
    ('sergio.pabon@abcflex.com.co',      NULL,      'DEVOPS')
) AS a(email, team, role)
JOIN users u ON u.email = a.email;

-- **********************************
-- ******** Table Dimensions ********
-- **********************************

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

INSERT INTO metrics (dimension, assignment, value, observation, measured_at)
SELECT m.dimension, a.id, m.value, m.observation, TIMESTAMPTZ '2025-12-19'
FROM (VALUES
    -- Team Alpha
    ('mateo.restrepo@abcflex.com.co',    'GENAI_DEV_ADOPTION', 'MODERATE',  NULL),
    ('valentina.ortiz@abcflex.com.co',   'GENAI_DEV_ADOPTION', 'MODERATE',  NULL),
    ('santiago.marin@abcflex.com.co',    'GENAI_DEV_ADOPTION', 'MODERATE',  'Problemas para la configuración del MCP de Azure DevOps'),
    ('camila.rojas@abcflex.com.co',      'GENAI_DEV_ADOPTION', 'MODERATE',  NULL),
    ('daniela.castro@abcflex.com.co',    'GENAI_QA_ADOPTION',  'LOW',       'Problemas para la configuración del MCP de Azure DevOps'),
    ('andres.pena@abcflex.com.co',       'GENAI_QA_ADOPTION',  'LOW',       'Configuración del MCP de Azure DevOps'),
    ('laura.gimenez@abcflex.com.co',     'GENAI_QA_ADOPTION',  'NO_USAGE',  NULL),

    -- Team Bravo
    ('felipe.cardenas@abcflex.com.co',   'GENAI_DEV_ADOPTION', 'MODERATE',  E'Configuración del MCP de Azure DevOps\nPrompts interesantes para varios frentes'),
    ('sofia.morales@abcflex.com.co',     'GENAI_DEV_ADOPTION', 'MODERATE',  'Configuración del MCP de Azure DevOps'),
    ('juan.herrera@abcflex.com.co',      'GENAI_DEV_ADOPTION', 'HIGH',      'Revisar definición de contexto para evitar workslop'),
    ('sebastian.lopez@abcflex.com.co',   'GENAI_DEV_ADOPTION', 'MODERATE',  'Revisar definición de contexto para evitar workslop'),
    ('isabella.vargas@abcflex.com.co',   'GENAI_DEV_ADOPTION', 'HIGH',      'Actualmente configurado y usando el MCP de Figma'),
    ('nicolas.gomez@abcflex.com.co',     'GENAI_DEV_ADOPTION', 'MODERATE',  'Configuración del MCP de Azure DevOps'),
    ('mariana.diaz@abcflex.com.co',      'GENAI_DEV_ADOPTION', 'UNDEFINED', NULL),
    ('david.sanchez@abcflex.com.co',     'GENAI_QA_ADOPTION',  'LOW',       'Configuración del MCP de Azure DevOps'),
    ('carolina.torres@abcflex.com.co',   'GENAI_QA_ADOPTION',  'NO_USAGE',  NULL),
    ('diego.ramirez@abcflex.com.co',     'GENAI_QA_ADOPTION',  'NO_USAGE',  NULL),

    -- Team Charlie
    ('alejandro.rios@abcflex.com.co',    'GENAI_DEV_ADOPTION', 'HIGH',      'Prompt para dividir HU y revisión de código'),
    ('manuela.suarez@abcflex.com.co',    'GENAI_DEV_ADOPTION', 'HIGH',      'Prompt para migración de SOAP a REST'),
    ('tomas.beltran@abcflex.com.co',     'GENAI_DEV_ADOPTION', 'HIGH',      E'Revisar definición de contexto para evitar workslop\nPrompts para sincronizar sprints y revisión de PR'),
    ('gabriela.mendoza@abcflex.com.co',  'GENAI_DEV_ADOPTION', 'UNDEFINED', NULL),
    ('samuel.acosta@abcflex.com.co',     'GENAI_DEV_ADOPTION', 'HIGH',      'Revisar definición de contexto para evitar workslop'),
    ('antonia.navarro@abcflex.com.co',   'GENAI_DEV_ADOPTION', 'HIGH',      NULL),
    ('emanuel.cortes@abcflex.com.co',    'GENAI_QA_ADOPTION',  'HIGH',      'Piloto de Multi-Agente en QA'),
    ('salome.guzman@abcflex.com.co',     'GENAI_QA_ADOPTION',  'HIGH',      'Prompts interesantes para varios frentes'),
    ('martin.quintero@abcflex.com.co',   'GENAI_QA_ADOPTION',  'VERY_HIGH', NULL),

    -- Team Delta
    ('lucas.forero@abcflex.com.co',      'GENAI_DEV_ADOPTION', 'VERY_HIGH', E'Uso de Copilot en 365 y modo plan en VSCode\nAspectos de arquitectura de referencia y documentación\nIngeniero de prompts (revisión y creador de prompts)\nPrompt de creador y revisor de HU y TC\nAgente asistentes de reuniones y proyecto de agente estimador'),
    ('valeria.pardo@abcflex.com.co',     'GENAI_DEV_ADOPTION', 'HIGH',      NULL),
    ('emiliano.salazar@abcflex.com.co',  'GENAI_DEV_ADOPTION', 'HIGH',      'Prompt de agregar proveedores'),
    ('renata.cabrera@abcflex.com.co',    'GENAI_DEV_ADOPTION', 'UNDEFINED', NULL),
    ('joaquin.pineda@abcflex.com.co',    'GENAI_DEV_ADOPTION', 'HIGH',      'Prompts interesantes para varios frentes'),
    ('luciana.bermudez@abcflex.com.co',  'GENAI_DEV_ADOPTION', 'HIGH',      NULL),
    ('maximiliano.duarte@abcflex.com.co','GENAI_QA_ADOPTION',  'HIGH',      'Tokens agotados'),
    ('sara.velasquez@abcflex.com.co',    'GENAI_QA_ADOPTION',  'NO_USAGE',  NULL),
    ('daniel.carmona@abcflex.com.co',    'GENAI_QA_ADOPTION',  'NO_USAGE',  NULL),

    -- Team Echo
    ('pablo.henao@abcflex.com.co',       'GENAI_DEV_ADOPTION', 'HIGH',      NULL),
    ('antonella.cano@abcflex.com.co',    'GENAI_DEV_ADOPTION', 'VERY_HIGH', NULL),
    ('simon.arias@abcflex.com.co',       'GENAI_DEV_ADOPTION', 'MODERATE',  'Problemas para la configuración del MCP de Azure DevOps'),
    ('juliana.mora@abcflex.com.co',      'GENAI_DEV_ADOPTION', 'VERY_HIGH', NULL),
    ('esteban.ospina@abcflex.com.co',    'GENAI_DEV_ADOPTION', 'HIGH',      NULL),
    ('catalina.franco@abcflex.com.co',   'GENAI_DEV_ADOPTION', 'HIGH',      'Prompt para GitFlow'),
    ('matias.rincon@abcflex.com.co',     'GENAI_DEV_ADOPTION', 'HIGH',      E'Revisar definición de contexto para evitar workslop\nPrompt de revisión de logs'),
    ('paulina.galvis@abcflex.com.co',    'GENAI_QA_ADOPTION',  'NO_USAGE',  NULL),
    ('ivan.montoya@abcflex.com.co',      'GENAI_QA_ADOPTION',  'HIGH',      NULL),
    ('natalia.cifuentes@abcflex.com.co', 'GENAI_QA_ADOPTION',  'MODERATE',  NULL),

    -- Cross-cutting roles (no team)
    ('ricardo.bedoya@abcflex.com.co',    'GENAI_DEV_ADOPTION', 'LOW',       'Configuración del MCP de Azure DevOps'),
    ('adriana.velez@abcflex.com.co',     'GENAI_DEV_ADOPTION', 'HIGH',      'Prompts para la arquitectura de referencia'),
    ('oscar.patino@abcflex.com.co',      'GENAI_DEV_ADOPTION', 'HIGH',      NULL),
    ('hernan.giraldo@abcflex.com.co',    'GENAI_DEV_ADOPTION', 'UNDEFINED', NULL),
    ('patricia.londono@abcflex.com.co',  'GENAI_DEV_ADOPTION', 'UNDEFINED', NULL),
    ('roberto.aguirre@abcflex.com.co',   'GENAI_DEV_ADOPTION', 'VERY_HIGH', NULL),
    ('lorena.bautista@abcflex.com.co',   'GENAI_QA_ADOPTION',  'HIGH',      'Problemas para la Configuración del MCP de Azure DevOps'),
    ('carmen.salgado@abcflex.com.co',    'GENAI_QA_ADOPTION',  'MODERATE',  'Problemas para la Configuración del MCP de Azure DevOps'),
    ('wilmer.trujillo@abcflex.com.co',   'GENAI_DEV_ADOPTION', 'UNDEFINED', NULL),
    ('sergio.pabon@abcflex.com.co',      'GENAI_DEV_ADOPTION', 'UNDEFINED', NULL)
) AS m(email, dimension, value, observation)
JOIN users u ON u.email = m.email
JOIN assignments a ON a.user_id = u.id;
