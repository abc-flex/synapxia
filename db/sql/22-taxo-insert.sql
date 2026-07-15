-- **********************************
-- ******* Table categories *********
-- **********************************

INSERT INTO categories (code, name, description, parent, option) VALUES
    ('AI_ASSETS', 'AI Assets', 'Category for all AI-related assets', NULL, NULL),
    ('CLASSIC_AI', 'Classic AI', 'Category for Classic AI assets', 'AI_ASSETS', NULL),
    ('GEN_AI', 'Generative AI', 'Category for Generative AI assets', 'AI_ASSETS', NULL);
    -- Classic AI and Machine Learning Models
    ('CLASSIC_AI', 'Classic AI', 'Category for Classic AI assets', 'AI_ASSETS', NULL),
    ('ML_MODELS', 'Machine Learning Models', 'Category for Machine Learning Models', 'CLASSIC_AI', NULL),
    ('ALGORITHMS', 'Algorithms', 'Category for Algorithms', 'CLASSIC_AI', NULL),
    ('DATASETS', 'Datasets', 'Category for Datasets', 'CLASSIC_AI', NULL),
    -- Generative AI
    ('GEN_AI', 'Generative AI', 'Category for Generative AI assets', 'AI_ASSETS', NULL),
    ('PROMPTS', 'Prompts', 'Category for Prompt', 'GEN_AI', '/lib/prompts'),
    ('MCPS', 'Model Context Protocol', 'Category for MCPs servers and clients definitions', 'GEN_AI', '/lib/mcps'),
    ('AGENTS', 'Agents', 'Category for AI Agents', 'GEN_AI', '/lib/agents'),
    ('AI_FLOWS', 'AI Flows', 'Category for Generative AI Flows in N8n', 'GEN_AI', NULL),
    ('SKILLS', 'Skills', 'Category for AI Skills in Generative AI tools', 'GEN_AI', NULL),
    ('ASSISTANTS', 'Assistants aka GPTs', 'Category for AI Assistants in ChatGPT', 'GEN_AI', NULL),
    ('RAG_APPS', 'RAG Apps', 'Category for Retrieval-Augmented Generation applications', 'GEN_AI', NULL),
    ('GEN_AI_MODELS', 'Gen AI Models', 'Category for Gen AI Models', 'GEN_AI', NULL);

-- **********************************
-- ******* Table features ****
-- **********************************

INSERT INTO features (code, name, type, description, list) VALUES
    -- Features that are useful for any digital asset with list of features
    ('LANGUAGE', 'Programming language', 'TECHNICAL',
    'The programming language used in the digital asset.', 'LANGUAGE'),
    -- Features primarily for MCPS with list of features
    ('MODE', 'Mode of operation', 'GENERAL',
    'The mode of operation for the digital asset, such as local or remote.', 'EXECUTION_MODE');

INSERT INTO features (code, name, type, description) VALUES
    -- Features that are useful for any digital asset
    ('PLATFORM', 'Digital asset platform', 'TECHNICAL',
    'Platform for the execution, deployment or storage of the digital asset.'),
    ('REPOSITORY', 'Asset repository', 'TECHNICAL',
    'The repository where the digital asset is hosted.'),
    ('FRAMEWORK', 'Web framework', 'TECHNICAL',
    'The web framework used in the digital asset.'),
    ('COMPLEXITY', 'Complexity level', 'GENERAL',
    'The complexity level of the digital asset.'),

    -- Features primarily for PROMPTS
    ('SUGGESTED_MODEL', 'Suggested model', 'TECHNICAL',
    'The AI model recommended for optimal performance of the digital asset.'),
    ('SUGGESTED_TEMPERATURE', 'Suggested temperature', 'TECHNICAL',
    'The temperature setting recommended for optimal performance of the digital asset.'),
    ('PROMPT_TEMPLATE', 'Prompt template', 'TECHNICAL',
    'The template structure used in the prompt to guide AI responses.'),
    ('EXAMPLE_OUTPUT', 'Example output', 'USABILITY',
    'Example output of the digital asset.'),

    -- Features primarily for MCPS
    ('OVERVIEW', 'Overview', 'GENERAL',
    'Overview of the digital asset with business problem solved, key capabilities or ROI impact.'),
    ('CONTENT', 'Content', 'TECHNICAL',
    'The content of the digital asset, such as avaliable resources, examples and/or documentation.'),
    ('TOOLS', 'Tools used', 'TECHNICAL',
    'List of asset tools and their available functions or capabilities.'),
    ('SERVER_CONFIG', 'JSON Server configuration', 'TECHNICAL',
    'Server Config Streamable Http in JSON format.'),

    -- Features primarily for AGENTS (with PROMPTS features as well)
    ('INSTRUCTIONS', 'Instructions', 'GENERAL',
    'The instructions for the digital asset, such as the agent goals and procedures.');

-- **********************************
-- ****** Table specifications ******
-- **********************************

INSERT INTO specifications (category, feature, default_value, required, sort_order) VALUES
    -- Features for a PROMPT category
    ('PROMPTS', 'PROMPT_TEMPLATE', NULL, TRUE, 10),
    ('PROMPTS', 'PLATFORM', 'VSCode', FALSE, 20),
    ('PROMPTS', 'SUGGESTED_MODEL', 'GPT-5', FALSE, 30),
    ('PROMPTS', 'SUGGESTED_TEMPERATURE', '0.2', FALSE, 40),
    ('PROMPTS', 'EXAMPLE_OUTPUT', NULL, FALSE, 50),

    -- Features for a MCPS category
    ('MCPS', 'OVERVIEW', NULL, TRUE, 10),
    ('MCPS', 'CONTENT', NULL, FALSE, 20),
    ('MCPS', 'MODE', 'Remote', FALSE, 30),
    ('MCPS', 'TOOLS', NULL, FALSE, 40),
    ('MCPS', 'SERVER_CONFIG', NULL, FALSE, 50),

    -- Features for a AGENT category
    ('AGENTS', 'INSTRUCTIONS', NULL, TRUE, 10),
    ('AGENTS', 'PLATFORM', 'VSCode', FALSE, 20),
    ('AGENTS', 'SUGGESTED_MODEL', 'GPT-5', FALSE, 30),
    ('AGENTS', 'SUGGESTED_TEMPERATURE', '0.2', FALSE, 40),
    ('AGENTS', 'TOOLS', NULL, FALSE, 50);
