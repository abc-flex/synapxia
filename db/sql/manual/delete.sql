-- **********************************
-- ****** Tables Initiatives ********
-- **********************************

DELETE FROM related_inits;
DELETE FROM favorite_inits;
DELETE FROM diagnostics;
DELETE FROM criterias;
DELETE FROM collaborations;
DELETE FROM initiatives;

-- **********************************
-- ******** Tables Library **********
-- **********************************

DELETE FROM related_assets;
DELETE FROM favorite_assets;
DELETE FROM characterizations;
DELETE FROM actions;
DELETE FROM assets;

-- **********************************
-- ***** Tables Collaboration *******
-- **********************************

DELETE FROM metrics;
DELETE FROM dimensions;
DELETE FROM assignments;
DELETE FROM projects;
DELETE FROM teams;

-- **********************************
-- ******* Tables Taxonomy **********
-- **********************************

DELETE FROM specifications;
DELETE FROM features;
DELETE FROM categories;

-- **********************************
-- ***** Tables Administration ******
-- **********************************

DELETE FROM privileges;
DELETE FROM options;
DELETE FROM users;
DELETE FROM roles;
DELETE FROM list_items;
DELETE FROM lists;
DELETE FROM business_units;
DELETE FROM modules;