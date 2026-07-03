-- **********************************
-- ***** Tables Digital Taxonomy ****
-- **********************************

-- Table categories
CREATE TABLE categories (
    code        VARCHAR(50)  NOT NULL,
    name        VARCHAR(100) NOT NULL,
    description VARCHAR(500),
    parent      VARCHAR(50),
    icon        TEXT,
    is_active   BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ,
    CONSTRAINT pk_categories PRIMARY KEY (code)
);

-- Table features
CREATE TABLE features (
    code        VARCHAR(50)  NOT NULL,
    name        VARCHAR(100) NOT NULL,
    description VARCHAR(500),
	type	    VARCHAR(100), -- references List_items.value where list='FEAT_TYPE'
    list        VARCHAR(50),  -- references Lists.code where type='FEATURE'
    is_active   BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ,
    CONSTRAINT pk_features PRIMARY KEY (code)
);

-- Table specifications
CREATE TABLE specifications (
    category        VARCHAR(50)   NOT NULL,
    feature         VARCHAR(50)   NOT NULL,
    default_value   TEXT, -- Any or references List_items.value where list IN [select code from lists where type='FEATURE']
    required        BOOLEAN       NOT NULL DEFAULT FALSE, -- feature must be filled when proposing/characterizing an asset of this category
    sort_order      INTEGER       NOT NULL DEFAULT 0,
    is_active       BOOLEAN       NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ,
    CONSTRAINT pk_specifications PRIMARY KEY (category, feature)
);

-- ****************************************
-- ************ Foreign Keys **************
-- ****************************************

-- categories.parent → categories.code
ALTER TABLE categories
    ADD CONSTRAINT fk_categories_categories
    FOREIGN KEY (parent)
    REFERENCES categories(code);

-- specifications.category → categories.code
ALTER TABLE specifications
    ADD CONSTRAINT fk_specs_categories
    FOREIGN KEY (category)
    REFERENCES categories(code);

-- specifications.feature → features.code
ALTER TABLE specifications
    ADD CONSTRAINT fk_specs_features
    FOREIGN KEY (feature)
    REFERENCES features (code);

-- features.list → lists.code
ALTER TABLE features
    ADD CONSTRAINT fk_features_lists
    FOREIGN KEY (list)
    REFERENCES lists (code);

-- **********************************
-- ***** Table lists/list_items *****
-- **********************************

-- ===== List: Feature Type =====
INSERT INTO lists (code, name, description, type, module) VALUES (
    'FEAT_TYPE', 'List of feature types for system configuration',
    'List that classifies the types of features (e.g., General, Technical, Commercial, Usability, Documentation and Platform) available in SynapxIA.',
    'LIST_OF_VALUES', 'TAXO');
INSERT INTO list_items (list, lang, value, label, sort_order) VALUES
    ('FEAT_TYPE', 'en', 'GENERAL',       'General',       10),
    ('FEAT_TYPE', 'en', 'TECHNICAL',     'Technical',     20),
    ('FEAT_TYPE', 'en', 'COMMERCIAL',    'Commercial',    30),
    ('FEAT_TYPE', 'en', 'USABILITY',     'Usability',     40),
    ('FEAT_TYPE', 'en', 'DOCUMENTATION', 'Documentation', 50);

-- ===== List of features: Programming Languages =====
INSERT INTO lists (code, name, description, type, module) VALUES (
    'LANGUAGE', 'List of programming languages for system configuration',
    'List that classifies the programming languages available in SynapxIA.',
    'FEATURE', 'TAXO');
INSERT INTO list_items (list, lang, value, label, sort_order) VALUES
    ('LANGUAGE', 'en', 'PYTHON',     'Python',     10),
    ('LANGUAGE', 'en', 'JAVASCRIPT', 'JavaScript', 20),
    ('LANGUAGE', 'en', 'JAVA',       'Java',       30),
    ('LANGUAGE', 'en', 'CPLUSPLUS',  'C++',        40),
    ('LANGUAGE', 'en', 'CSHARP',     'C#',         50);

-- ===== List of features: Execution Modes =====
INSERT INTO lists (code, name, description, type, module) VALUES (
    'EXECUTION_MODE', 'List of execution modes for system configuration',
    'List that classifies the execution modes available in SynapxIA.',
    'FEATURE', 'TAXO');
INSERT INTO list_items (list, lang, value, label, sort_order) VALUES
    ('EXECUTION_MODE', 'en', 'LOCAL',    'Local',    10),
    ('EXECUTION_MODE', 'en', 'REMOTE',   'Remote',   20);