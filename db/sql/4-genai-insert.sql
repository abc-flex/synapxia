-- **********************************
-- ******* Table categories *********
-- **********************************

INSERT INTO categories (code, name, description, parent, created_at) VALUES
    ('AI_ASSETS', 'AI Assets', 'Category for all AI-related assets', NULL, NOW()),
    -- Classic AI and Machine Learning Models
    ('CLASSIC_AI', 'Classic AI', 'Category for Classic AI assets', 'AI_ASSETS', NOW()),
    ('ML_MODELS', 'Machine Learning Models', 'Category for Machine Learning Models', 'CLASSIC_AI', NOW()),
    ('ALGORITHMS', 'Algorithms', 'Category for Algorithms', 'CLASSIC_AI', NOW()),
    ('DATASETS', 'Datasets', 'Category for Datasets', 'CLASSIC_AI', NOW()),
    -- Generative AI
    ('GEN_AI', 'Generative AI', 'Category for Generative AI assets', 'AI_ASSETS', NOW()),
    ('PROMPTS', 'Prompt', 'Category for Prompt', 'GEN_AI', NOW()),
    ('MCPS', 'Model Context Protocol', 'Category for MCPs servers and clients definitions', 'GEN_AI', NOW()),
    ('AGENTS', 'Agents', 'Category for AI Agents', 'GEN_AI', NOW()),
    ('AI_FLOWS', 'AI Flows', 'Category for Generative AI Flows in N8n', 'GEN_AI', NOW()),
    ('ASSISTANTS', 'Assistants aka GPTs', 'Category for AI Assistants in ChatGPT', 'GEN_AI', NOW());

-- **********************************
-- ******* Table assets *************
-- **********************************

INSERT INTO assets (code, name, reference, description, type, category, status, visibility, tags, created_at) VALUES
    (1, 'Python Web Development Incremental Prompt', 'python-web-increment.prompt.md',
    'A prompt designed to guide AI in incrementally developing web applications using Python.',
    'RESOURCE','PROMPTS', 'IN_USE', 'PUBLIC', '{"python", "web", "development"}', NOW()),
    (2, 'Python Web Developer Agent', 'python-web-dev.agent.md',
    'An AI agent specialized in developing web applications using Python frameworks.',
    'RESOURCE','AGENTS', 'IN_USE', 'PUBLIC', '{"python", "web", "agent"}', NOW());

-- **********************************
-- ******* Table characteristics ****
-- **********************************

INSERT INTO characteristics (asset, characteristic, value, detail, created_at) VALUES
    -- Characteristics for PY_WEB_INCREMENT
    ('PY_WEB_INCREMENT', 'language', 'Python', 'The programming language used in the prompt.', NOW()),
    ('PY_WEB_INCREMENT', 'framework', 'Django', 'The web framework targeted by the prompt.', NOW()),
    ('PY_WEB_INCREMENT', 'complexity', 'Intermediate', 'The complexity level of the web applications to be developed.', NOW()),
    -- Characteristics for PY_WEB_DEV_AGENT
    ('PY_WEB_DEV_AGENT', 'language', 'Python', 'The programming language the agent specializes in.', NOW()),
    ('PY_WEB_DEV_AGENT', 'framework', 'Flask', 'The web framework the agent is proficient with.', NOW()),
    ('PY_WEB_DEV_AGENT', 'capability', 'Full-stack Development', 'The development capabilities of the agent.', NOW());