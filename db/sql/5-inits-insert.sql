-- **********************************
-- ****** Lists for Criterias *******
-- **********************************

INSERT INTO lists (code, name, description, module, type) VALUES
('CLARITY_MATURITY', 'Clarity and maturity of the need', 'Level of definition of the need', 'INITS', 'CRITERIA'),
('SUPPORT_OBJECTIVE', 'Support objective', 'Type of support required', 'INITS', 'CRITERIA'),
('COMPLEXITY', 'Technical and functional complexity', 'Level of solution complexity', 'INITS', 'CRITERIA'),
('DATA_INTEGRATIONS', 'Data and integrations', 'Use of data and integrations', 'INITS', 'CRITERIA'),
('RISK_IMPACT', 'Operational risk and impact', 'Level of operational risk', 'INITS', 'CRITERIA'),
('SUSTAINABILITY', 'Sustainability and expected adoption level', 'Level of usage and adoption', 'INITS', 'CRITERIA');

-- ===== 1. Clarity and maturity =====
INSERT INTO list_items (list, value, label, sort_order) VALUES
('CLARITY_MATURITY', '1', 'Exploratory or not yet well defined', 1),
('CLARITY_MATURITY', '2', 'Partially defined and requires validation', 2),
('CLARITY_MATURITY', '3', 'Scope and objectives are clearly defined', 3);
-- 1. Traducciones para Claridad y madurez
INSERT INTO item_translations (list, value, lang, label) VALUES
('CLARITY_MATURITY', '1', 'es', 'Exploratoria o aún no está bien definida'),
('CLARITY_MATURITY', '2', 'es', 'Definida de forma parcial y requiere validación'),
('CLARITY_MATURITY', '3', 'es', 'El alcance y los objetivos están claramente definidos');

-- ===== 2. Support objective =====
INSERT INTO list_items (list, value, label, sort_order) VALUES
('SUPPORT_OBJECTIVE', '1', 'Requires guidance, training, recommendations, or templates', 1),
('SUPPORT_OBJECTIVE', '2', 'Requires validating an idea through testing or prototyping', 2),
('SUPPORT_OBJECTIVE', '3', 'Requires an operational solution for real use', 3);
-- 2. Traducciones para Objetivo del acompañamiento
INSERT INTO item_translations (list, value, lang, label) VALUES
('SUPPORT_OBJECTIVE', '1', 'es', 'Requiere guía, formación, recomendaciones o plantillas'),
('SUPPORT_OBJECTIVE', '2', 'es', 'Requiere validar una idea mediante prueba o prototipo'),
('SUPPORT_OBJECTIVE', '3', 'es', 'Requiere una solución operativa para uso real');

-- ===== 3. Technical complexity =====
INSERT INTO list_items (list, value, label, sort_order) VALUES
('COMPLEXITY', '1', 'Low; does not require complex design or significant process changes', 1),
('COMPLEXITY', '2', 'Medium; requires designing and testing a functional solution', 2),
('COMPLEXITY', '3', 'High; requires architecture, development, and significant process adjustments', 3);
-- 3. Traducciones para Complejidad técnica
INSERT INTO item_translations (list, value, lang, label) VALUES
('COMPLEXITY', '1', 'es', 'Baja; no requiere diseño complejo ni cambios relevantes en el proceso'),
('COMPLEXITY', '2', 'es', 'Media; requiere diseñar y probar una solución funcional'),
('COMPLEXITY', '3', 'es', 'Alta; requiere arquitectura, desarrollo y ajustes relevantes en el proceso');

-- ===== 4. Data and integrations =====
INSERT INTO list_items (list, value, label, sort_order) VALUES
('DATA_INTEGRATIONS', '1', 'Does not use critical data or require integrations', 1),
('DATA_INTEGRATIONS', '2', 'Uses limited data or possible integrations, but not critical', 2),
('DATA_INTEGRATIONS', '3', 'Uses real or sensitive data or integrates with systems, APIs, or institutional workflows', 3);
-- 4. Traducciones para Datos e integraciones
INSERT INTO item_translations (list, value, lang, label) VALUES
('DATA_INTEGRATIONS', '1', 'es', 'No usa datos críticos ni requiere integraciones'),
('DATA_INTEGRATIONS', '2', 'es', 'Usa datos limitados o integraciones posibles, pero no críticas'),
('DATA_INTEGRATIONS', '3', 'es', 'Usa datos reales o sensibles o integración con sistemas, APIs o flujos institucionales');

-- ===== 5. Risk and impact =====
INSERT INTO list_items (list, value, label, sort_order) VALUES
('RISK_IMPACT', '1', 'Low risk; errors have no significant consequences', 1),
('RISK_IMPACT', '2', 'Medium risk; requires validation before broader use', 2),
('RISK_IMPACT', '3', 'High risk; may affect operations, decisions, users, or compliance', 3);
-- 5. Riesgo e impacto
INSERT INTO item_translations (list, value, lang, label) VALUES
('RISK_IMPACT', '1', 'es', 'Riesgo bajo; error sin consecuencias relevantes'),
('RISK_IMPACT', '2', 'es', 'Riesgo medio; requiere validación antes de uso más amplio'),
('RISK_IMPACT', '3', 'es', 'Riesgo alto; puede afectar operación, decisiones, usuarios o cumplimiento');

-- ===== 6. Sustainability and adoption =====
INSERT INTO list_items (list, value, label, sort_order) VALUES
('SUSTAINABILITY', '1', 'One-time or learning use; does not require continuous operation', 1),
('SUSTAINABILITY', '2', 'Recurring use, but still under evaluation', 2),
('SUSTAINABILITY', '3', 'Continuous use; requires knowledge transfer, ownership, and evolution over time', 3);
-- 6. Sostenibilidad
INSERT INTO item_translations (list, value, lang, label) VALUES
('SUSTAINABILITY', '1', 'es', 'Uso puntual o de aprendizaje; no requiere operación continua'),
('SUSTAINABILITY', '2', 'es', 'Uso recurrente, pero aún en evaluación'),
('SUSTAINABILITY', '3', 'es', 'Uso continuo; requiere transferencia, apropiación y evolución en el tiempo');

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