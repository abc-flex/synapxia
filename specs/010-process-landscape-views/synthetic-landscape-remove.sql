-- Removes everything synthetic-landscape.sql wrote: rows whose process codes
-- start with `SYN-` (links and relations first, then the processes, children
-- before parents). Touches no other row.

BEGIN;

DELETE FROM process_inits     WHERE process LIKE 'SYN-%';
DELETE FROM process_assets    WHERE process LIKE 'SYN-%';
DELETE FROM related_processes WHERE source LIKE 'SYN-%' OR target LIKE 'SYN-%';
UPDATE processes SET parent = NULL WHERE code LIKE 'SYN-%';
DELETE FROM processes         WHERE code LIKE 'SYN-%';

COMMIT;
