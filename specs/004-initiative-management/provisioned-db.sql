-- Initiative Management (004) — bring an already-provisioned DB in line with the seeds.
-- Idempotent: safe to run more than once.
BEGIN;

INSERT INTO list_items (list, lang, value, label, sort_order) VALUES
    ('COLLAB_TYPE', 'en', 'KICKOFF', 'Kickoff', 55),
    ('EXPECTED_IMPACT', 'es', 'TIME_REDUCTION', 'Reducción de tiempo', 10),
    ('EXPECTED_IMPACT', 'es', 'QUALITY_IMPROVEMENT', 'Mejora de calidad', 20),
    ('EXPECTED_IMPACT', 'es', 'ERROR_REDUCTION', 'Reducción de errores', 30),
    ('EXPECTED_IMPACT', 'es', 'DECISION_SUPPORT', 'Apoyo a la toma de decisiones', 40),
    ('EXPECTED_IMPACT', 'es', 'IMPROVED_UX', 'Mejor experiencia de usuario', 50),
    ('EXPECTED_IMPACT', 'es', 'COST_SAVINGS', 'Ahorro de costos', 60),
    ('EXPECTED_IMPACT', 'es', 'REVENUE_INCREASE', 'Aumento de ingresos', 70),
    ('EXPECTED_IMPACT', 'es', 'COMPLIANCE_ENHANCEMENT', 'Mejora del cumplimiento', 80),
    ('EXPECTED_IMPACT', 'es', 'RISK_REDUCTION', 'Reducción de riesgos', 90),
    ('EXPECTED_IMPACT', 'es', 'SCALABILITY_IMPROVEMENT', 'Mejora de escalabilidad', 100),
    ('EXPECTED_IMPACT', 'es', 'INNOVATION', 'Innovación', 110),
    ('EXPECTED_IMPACT', 'es', 'OTHER', 'Otro', 120),
    ('PRIORITY_LEVEL', 'es', 'HIGH', 'Alta', 10),
    ('PRIORITY_LEVEL', 'es', 'MEDIUM', 'Media', 20),
    ('PRIORITY_LEVEL', 'es', 'LOW', 'Baja', 30),
    ('INITIATIVE_TYPE', 'es', 'EXPLORATION', 'Exploración', 10),
    ('INITIATIVE_TYPE', 'es', 'PROTOTYPING', 'Prototipado', 20),
    ('INITIATIVE_TYPE', 'es', 'IMPLEMENTATION', 'Implementación', 30),
    ('INITIATIVE_STATUS', 'es', 'ACTIVATED', 'Activada', 10),
    ('INITIATIVE_STATUS', 'es', 'FEEDBACK', 'Retroalimentación', 20),
    ('INITIATIVE_STATUS', 'es', 'ACCEPTED', 'Aceptada', 30),
    ('INITIATIVE_STATUS', 'es', 'REJECTED', 'Rechazada', 40),
    ('INITIATIVE_STATUS', 'es', 'IN_PROGRESS', 'En progreso', 50),
    ('INITIATIVE_STATUS', 'es', 'DELIVERED', 'Entregada', 60),
    ('INITIATIVE_STATUS', 'es', 'ARCHIVED', 'Archivada', 70),
    ('COLLAB_TYPE', 'es', 'ACTIVATION', 'Activación', 10),
    ('COLLAB_TYPE', 'es', 'DIAGNOSIS', 'Diagnóstico', 20),
    ('COLLAB_TYPE', 'es', 'MODIFICATION', 'Modificación', 30),
    ('COLLAB_TYPE', 'es', 'ACCEPTANCE', 'Aceptación', 40),
    ('COLLAB_TYPE', 'es', 'REJECTION', 'Rechazo', 50),
    ('COLLAB_TYPE', 'es', 'KICKOFF', 'Arranque', 55),
    ('COLLAB_TYPE', 'es', 'DELIVERY', 'Entrega', 60),
    ('COLLAB_TYPE', 'es', 'ARCHIVING', 'Archivo', 70),
    ('COLLAB_TYPE', 'es', 'VOTE', 'Voto', 80),
    ('COLLAB_TYPE', 'es', 'COMMENT', 'Comentario', 90),
    ('COLLAB_TYPE', 'es', 'QUESTION', 'Pregunta', 100),
    ('COLLAB_TYPE', 'es', 'ANSWER', 'Respuesta', 110)
ON CONFLICT (list, lang, value) DO NOTHING;

UPDATE initiatives SET status = 'IN_PROGRESS', type = 'IMPLEMENTATION' WHERE id = 1;
UPDATE initiatives SET status = 'DELIVERED',   type = 'IMPLEMENTATION' WHERE id = 2;
UPDATE initiatives SET status = 'ACCEPTED',    type = 'PROTOTYPING'    WHERE id = 3;
UPDATE initiatives SET status = 'ACTIVATED',   type = 'EXPLORATION'    WHERE id = 4;
UPDATE initiatives SET status = 'ACTIVATED',   type = 'EXPLORATION'    WHERE id = 5;

-- Mirrors db/sql/32-collab-insert.sql. The test grants for this user are NOT part
-- of the seed: see test-owner.sql.
UPDATE users SET profile = 'ADMINISTRATIVE' WHERE username = 'felipe.cardenas';

-- The seeded ANSWER threads to its QUESTION (id 11), not to an ACCEPTANCE row.
UPDATE collaborations SET parent = 11 WHERE id = 12 AND type = 'ANSWER' AND parent = 5;

COMMIT;
