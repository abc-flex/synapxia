-- Dashboard Management (specs/006-dashboard-management) — provisioned databases.
--
-- A fresh volume (`make rebuild`) already gets these rows from db/sql/61-ana-ddl.sql.
-- Run this ONCE against a database provisioned before 006 (local volume kept, Neon)
-- so the analytics lists follow the header language switcher. Safe to rerun: each
-- row is inserted only when it is missing.

INSERT INTO list_items (list, lang, value, label, sort_order)
SELECT v.list, 'es', v.value, v.label, v.sort_order
FROM (VALUES
    ('DASHBOARD_TYPE',   'DASHBOARD',       'Tablero',              10),
    ('DASHBOARD_TYPE',   'REPORT',          'Informe',              20),
    ('DASHBOARD_TYPE',   'SCORECARD',       'Cuadro de mando',      30),
    ('DASHBOARD_TYPE',   'KPI_VIEW',        'Vista de KPI',         40),
    ('DASHBOARD_TYPE',   'ANALYTICAL_VIEW', 'Vista analítica',      50),
    ('SOURCE_TYPE',      'INTERNAL_PAGE',   'Página interna',       10),
    ('SOURCE_TYPE',      'POWER_BI',        'Power BI',             20),
    ('SOURCE_TYPE',      'LOOKER_STUDIO',   'Looker Studio',        30),
    ('SOURCE_TYPE',      'TABLEAU',         'Tableau',              40),
    ('SOURCE_TYPE',      'QLIK_SENSE',      'Qlik Sense',           50),
    ('SOURCE_TYPE',      'METABASE',        'Metabase',             60),
    ('SOURCE_TYPE',      'SUPERSET',        'Superset',             70),
    ('SOURCE_TYPE',      'CUSTOM_IFRAME',   'Iframe personalizado', 80),
    ('DASHBOARD_STATUS', 'DRAFT',           'Borrador',             10),
    ('DASHBOARD_STATUS', 'PUBLISHED',       'Publicado',            20),
    ('DASHBOARD_STATUS', 'ARCHIVED',        'Archivado',            30),
    ('DASHBOARD_STATUS', 'RETIRED',         'Retirado',             40),
    ('PARAM_TYPE',       'STRING',          'Texto',                10),
    ('PARAM_TYPE',       'NUMBER',          'Número',               20),
    ('PARAM_TYPE',       'BOOLEAN',         'Booleano',             30),
    ('PARAM_TYPE',       'DATE',            'Fecha',                40),
    ('EXECUTION_STATUS', 'SUCCESS',         'Exitosa',              10),
    ('EXECUTION_STATUS', 'FAILED',          'Fallida',              20),
    ('EXECUTION_STATUS', 'CANCELLED',       'Cancelada',            30),
    ('EXECUTION_STATUS', 'TIMEOUT',         'Tiempo agotado',       40),
    ('EXECUTION_STATUS', 'UNAUTHORIZED',    'No autorizada',        50)
) AS v(list, value, label, sort_order)
WHERE NOT EXISTS (
    SELECT 1 FROM list_items li
    WHERE li.list = v.list AND li.lang = 'es' AND li.value = v.value
);
