UPDATE snapshot SET mounted = false WHERE mounted is NULL;

ALTER TABLE IF EXISTS snapshot ALTER COLUMN mounted SET NOT NULL;
