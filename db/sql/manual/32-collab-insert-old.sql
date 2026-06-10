-- **********************************
-- ********** Table Roles ***********
-- **********************************

INSERT INTO roles (code, name, description) VALUES
    ('BACK',  'Backend Developer',  'Responsible for server-side development, APIs, data access and integration with external services, ensuring performance, security and scalability.'),
    ('FRONT', 'Frontend Developer', 'Responsible for user interface implementation, client-side logic and interaction patterns, ensuring usability, accessibility and a consistent user experience.'),
    ('QA',    'QA Engineer',        'Responsible for designing and executing tests, validating quality criteria and helping prevent defects through automated and manual testing practices.'),
    ('PO',    'Product Owner',      'Responsible for defining product vision and priorities, managing the backlog and collaborating with stakeholders to maximize delivered business value.'),
    ('TL',    'Team Lead',          'Responsible for guiding the team technically and operationally, facilitating collaboration, removing blockers and aligning delivery with agreed objectives.');


-- **********************************
-- ********** Table Teams ***********
-- **********************************

INSERT INTO teams (code, name, description)
VALUES
    ('CORE',      'Core Engineering Squad',      'Multidisciplinary team in charge of building and maintaining shared platform components and technical foundations.'),
    ('SUPPORT',   'Customer Support Solutions',  'Team focused on solutions that support customer-facing operations, incidents and service request workflows.'),
    ('OPS',       'Operations & Automation',     'Team dedicated to process optimization, automation and reliability of internal operational workflows.'),
    ('ANALYTICS', 'Analytics & Insights',        'Team responsible for analytical solutions, dashboards and data products that support decision-making.'),
    ('LAB',       'Innovation Lab',              'Exploratory team oriented to experiments, prototypes and proofs of concept for new ideas and technologies.');

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
        -- 1–12  (CORE team)
        ('juan.perez',        'juan.perez@synapxia.local',        'Juan',      'Perez',        'TL'),
        ('maria.rodriguez',   'maria.rodriguez@synapxia.local',   'Maria',     'Rodriguez',    'PO'),
        ('carlos.gomez',      'carlos.gomez@synapxia.local',      'Carlos',    'Gomez',        'PO'),
        ('ana.martinez',      'ana.martinez@synapxia.local',      'Ana',       'Martinez',     'BACK'),
        ('luis.lopez',        'luis.lopez@synapxia.local',        'Luis',      'Lopez',        'BACK'),
        ('diana.ramirez',     'diana.ramirez@synapxia.local',     'Diana',     'Ramirez',      'BACK'),
        ('andres.diaz',       'andres.diaz@synapxia.local',       'Andres',    'Diaz',         'FRONT'),
        ('paula.torres',      'paula.torres@synapxia.local',      'Paula',     'Torres',       'FRONT'),
        ('jorge.morales',     'jorge.morales@synapxia.local',     'Jorge',     'Morales',      'FRONT'),
        ('laura.herrera',     'laura.herrera@synapxia.local',     'Laura',     'Herrera',      'QA'),
        ('camilo.castillo',   'camilo.castillo@synapxia.local',   'Camilo',    'Castillo',     'QA'),
        ('natalia.vargas',    'natalia.vargas@synapxia.local',    'Natalia',   'Vargas',       'QA'),

        -- 13–24 (SUPPORT team)
        ('sebastian.rios',    'sebastian.rios@synapxia.local',    'Sebastian', 'Rios',         'TL'),
        ('andrea.mejia',      'andrea.mejia@synapxia.local',      'Andrea',    'Mejia',        'PO'),
        ('felipe.suarez',     'felipe.suarez@synapxia.local',     'Felipe',    'Suarez',       'PO'),
        ('valentina.duarte',  'valentina.duarte@synapxia.local',  'Valentina', 'Duarte',       'BACK'),
        ('santiago.pineda',   'santiago.pineda@synapxia.local',   'Santiago',  'Pineda',       'BACK'),
        ('carolina.silva',    'carolina.silva@synapxia.local',    'Carolina',  'Silva',        'BACK'),
        ('daniel.cardenas',   'daniel.cardenas@synapxia.local',   'Daniel',    'Cardenas',     'FRONT'),
        ('juliana.salazar',   'juliana.salazar@synapxia.local',   'Juliana',   'Salazar',      'FRONT'),
        ('mauricio.valencia', 'mauricio.valencia@synapxia.local', 'Mauricio',  'Valencia',     'FRONT'),
        ('lina.guzman',       'lina.guzman@synapxia.local',       'Lina',      'Guzman',       'QA'),
        ('oscar.ordonez',     'oscar.ordonez@synapxia.local',     'Oscar',     'Ordonez',      'QA'),
        ('viviana.benitez',   'viviana.benitez@synapxia.local',   'Viviana',   'Benitez',      'QA'),

        -- 25–36 (OPS team)
        ('rodrigo.molina',    'rodrigo.molina@synapxia.local',    'Rodrigo',   'Molina',       'TL'),
        ('manuela.cabrera',   'manuela.cabrera@synapxia.local',   'Manuela',   'Cabrera',      'PO'),
        ('fabian.gallego',    'fabian.gallego@synapxia.local',    'Fabian',    'Gallego',      'PO'),
        ('sara.leon',         'sara.leon@synapxia.local',         'Sara',      'Leon',         'BACK'),
        ('alejandro.mora',    'alejandro.mora@synapxia.local',    'Alejandro', 'Mora',         'BACK'),
        ('claudia.pardo',     'claudia.pardo@synapxia.local',     'Claudia',   'Pardo',        'BACK'),
        ('hernan.acosta',     'hernan.acosta@synapxia.local',     'Hernan',    'Acosta',       'FRONT'),
        ('tatiana.becerra',   'tatiana.becerra@synapxia.local',   'Tatiana',   'Becerra',      'FRONT'),
        ('ivan.bustamante',   'ivan.bustamante@synapxia.local',   'Ivan',      'Bustamante',   'FRONT'),
        ('marcela.camargo',   'marcela.camargo@synapxia.local',   'Marcela',   'Camargo',      'QA'),
        ('edwin.chacon',      'edwin.chacon@synapxia.local',      'Edwin',     'Chacon',       'QA'),
        ('monica.cordoba',    'monica.cordoba@synapxia.local',    'Monica',    'Cordoba',      'QA'),

        -- 37–48 (ANALYTICS team)
        ('pedro.delgadillo',  'pedro.delgadillo@synapxia.local',  'Pedro',     'Delgadillo',   'TL'),
        ('angela.fonseca',    'angela.fonseca@synapxia.local',    'Angela',    'Fonseca',      'PO'),
        ('cristian.giraldo',  'cristian.giraldo@synapxia.local',  'Cristian',  'Giraldo',      'PO'),
        ('karen.hoyos',       'karen.hoyos@synapxia.local',       'Karen',     'Hoyos',        'BACK'),
        ('miguel.jaramillo',  'miguel.jaramillo@synapxia.local',  'Miguel',    'Jaramillo',    'BACK'),
        ('daniela.lozano',    'daniela.lozano@synapxia.local',    'Daniela',   'Lozano',       'BACK'),
        ('ricardo.maldonado', 'ricardo.maldonado@synapxia.local', 'Ricardo',   'Maldonado',    'FRONT'),
        ('patricia.nieto',    'patricia.nieto@synapxia.local',    'Patricia',  'Nieto',        'FRONT'),
        ('julian.ospina',     'julian.ospina@synapxia.local',     'Julian',    'Ospina',       'FRONT'),
        ('nelson.quintero',   'nelson.quintero@synapxia.local',   'Nelson',    'Quintero',     'QA'),
        ('veronica.restrepo', 'veronica.restrepo@synapxia.local', 'Veronica',  'Restrepo',     'QA'),
        ('hugo.salamanca',    'hugo.salamanca@synapxia.local',    'Hugo',      'Salamanca',    'QA'),

        -- 49–60 (LAB team)
        ('lorena.tovar',      'lorena.tovar@synapxia.local',      'Lorena',    'Tovar',        'TL'),
        ('german.uribe',      'german.uribe@synapxia.local',      'German',    'Uribe',        'PO'),
        ('adriana.velasquez', 'adriana.velasquez@synapxia.local', 'Adriana',   'Velasquez',    'PO'),
        ('victor.zamora',     'victor.zamora@synapxia.local',     'Victor',    'Zamora',       'BACK'),
        ('luz.barrios',       'luz.barrios@synapxia.local',       'Luz',       'Barrios',      'BACK'),
        ('wilson.bonilla',    'wilson.bonilla@synapxia.local',    'Wilson',    'Bonilla',      'BACK'),
        ('yolanda.caicedo',   'yolanda.caicedo@synapxia.local',   'Yolanda',   'Caicedo',      'FRONT'),
        ('edgar.castano',     'edgar.castano@synapxia.local',     'Edgar',     'Castano',      'FRONT'),
        ('beatriz.florez',    'beatriz.florez@synapxia.local',    'Beatriz',   'Florez',       'FRONT'),
        ('harold.sanchez',    'harold.sanchez@synapxia.local',    'Harold',    'Sanchez',      'QA'),
        ('gloria.moreno',     'gloria.moreno@synapxia.local',     'Gloria',    'Moreno',       'QA'),
        ('camila.navarro',    'camila.navarro@synapxia.local',    'Camila',    'Navarro',      'QA')
    ) AS v(username, email, first_name, last_name, menu_role)
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

-- Keep the identity sequence aligned with the explicit ids above
SELECT setval(pg_get_serial_sequence('users', 'id'), (SELECT MAX(id) FROM users));

-- **********************************
-- ******* Table Assignments ********
-- **********************************

INSERT INTO assignments (team, user_id, role)
VALUES
    -- CORE: users 1-12
    ('CORE', 1,  'TL'),
    ('CORE', 2,  'PO'),
    (NULL, 3,  'PO'),
    ('CORE', 4,  'BACK'),
    ('CORE', 5,  'BACK'),
    ('CORE', 6,  'BACK'),
    ('CORE', 7,  'FRONT'),
    ('CORE', 8,  'FRONT'),
    ('CORE', 9,  'FRONT'),
    ('CORE', 10, 'QA'),
    ('CORE', 11, 'QA'),
    ('CORE', 12, 'QA'),

    -- SUPPORT: users 13-24
    ('SUPPORT', 13, 'TL'),
    ('SUPPORT', 14, 'PO'),
    (NULL, 15, 'PO'),
    ('SUPPORT', 16, 'BACK'),
    ('SUPPORT', 17, 'BACK'),
    ('SUPPORT', 18, 'BACK'),
    ('SUPPORT', 19, 'FRONT'),
    ('SUPPORT', 20, 'FRONT'),
    ('SUPPORT', 21, 'FRONT'),
    ('SUPPORT', 22, 'QA'),
    ('SUPPORT', 23, 'QA'),
    ('SUPPORT', 24, 'QA'),

    -- OPS: users 25-36
    ('OPS', 25, 'TL'),
    ('OPS', 26, 'PO'),
    (NULL, 27, 'PO'),
    ('OPS', 28, 'BACK'),
    ('OPS', 29, 'BACK'),
    ('OPS', 30, 'BACK'),
    ('OPS', 31, 'FRONT'),
    ('OPS', 32, 'FRONT'),
    ('OPS', 33, 'FRONT'),
    ('OPS', 34, 'QA'),
    ('OPS', 35, 'QA'),
    ('OPS', 36, 'QA'),

    -- ANALYTICS: users 37-48
    ('ANALYTICS', 37, 'TL'),
    ('ANALYTICS', 38, 'PO'),
    ('ANALYTICS', 39, 'PO'),
    ('ANALYTICS', 40, 'BACK'),
    ('ANALYTICS', 41, 'BACK'),
    ('ANALYTICS', 42, 'BACK'),
    ('ANALYTICS', 43, 'FRONT'),
    ('ANALYTICS', 44, 'FRONT'),
    ('ANALYTICS', 45, 'FRONT'),
    ('ANALYTICS', 46, 'QA'),
    ('ANALYTICS', 47, 'QA'),
    (NULL, 48, 'QA'),

    -- LAB: users 49-60
    ('LAB', 49, 'TL'),
    ('LAB', 50, 'PO'),
    ('LAB', 51, 'PO'),
    ('LAB', 52, 'BACK'),
    ('LAB', 53, 'BACK'),
    ('LAB', 54, 'BACK'),
    ('LAB', 55, 'FRONT'),
    ('LAB', 56, 'FRONT'),
    ('LAB', 57, 'FRONT'),
    ('LAB', 58, 'QA'),
    ('LAB', 59, 'QA'),
    (NULL, 60, 'QA');
