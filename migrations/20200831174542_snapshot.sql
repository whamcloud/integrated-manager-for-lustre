CREATE TABLE IF NOT EXISTS snapshot (
  id serial PRIMARY KEY,
  filesystem_name TEXT NOT NULL,
  snapshot_name TEXT NOT NULL,
  create_time TIMESTAMP WITH TIME ZONE NOT NULL,
  modify_time TIMESTAMP WITH TIME ZONE NOT NULL,
  snapshot_fsname TEXT NOT NULL,
  mounted BOOLEAN NULL,
  comment TEXT NULL,
  UNIQUE (filesystem_name, snapshot_name)
);

CREATE OR REPLACE FUNCTION table_snapshot_update_notify() RETURNS TRIGGER AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    PERFORM pg_notify('table_update', '[ "' || TG_OP || '", "' || TG_TABLE_NAME || '", ' || row_to_json(NEW) || ']');
  ELSEIF TG_OP = 'UPDATE' AND OLD IS DISTINCT FROM NEW THEN
    PERFORM pg_notify('table_update', '[ "' || TG_OP || '", "' || TG_TABLE_NAME || '", ' || row_to_json(NEW) || ']');
  ELSE
    PERFORM pg_notify('table_update','[ "' || TG_OP || '", "' || TG_TABLE_NAME || '", ' || row_to_json(OLD) || ']');
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS snapshot_notify_update ON snapshot;

DROP TRIGGER IF EXISTS snapshot_notify_insert ON snapshot;

DROP TRIGGER IF EXISTS snapshot_notify_delete ON snapshot;

CREATE TRIGGER snapshot_notify_update
AFTER
UPDATE ON snapshot FOR EACH ROW EXECUTE PROCEDURE table_snapshot_update_notify();

CREATE TRIGGER snapshot_notify_insert
AFTER
INSERT ON snapshot FOR EACH ROW EXECUTE PROCEDURE table_snapshot_update_notify();

CREATE TRIGGER snapshot_notify_delete
AFTER DELETE ON snapshot FOR EACH ROW EXECUTE PROCEDURE table_snapshot_update_notify();

CREATE TABLE IF NOT EXISTS snapshot_configuration (
  id serial PRIMARY KEY,
  filesystem_name TEXT NOT NULL,
  use_barrier BOOLEAN NOT NULL,
  last_run TIMESTAMP WITH TIME ZONE,
  interval INTERVAL NOT NULL,
  keep_num INT
);

CREATE TYPE snapshot_delete_unit AS ENUM ('percent', 'gibibytes', 'tebibytes');

CREATE TABLE IF NOT EXISTS snapshot_retention (
  id serial PRIMARY KEY,
  filesystem_name TEXT NOT NULL,
  delete_num INT NOT NULL,
  delete_unit snapshot_delete_unit NOT NULL,
  last_run TIMESTAMP WITH TIME ZONE
)
