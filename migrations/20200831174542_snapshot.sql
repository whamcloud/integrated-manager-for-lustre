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

CREATE OR REPLACE FUNCTION table_update_notify() RETURNS TRIGGER AS $$
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
UPDATE ON snapshot FOR EACH ROW EXECUTE PROCEDURE table_update_notify();

CREATE TRIGGER snapshot_notify_insert
AFTER
INSERT ON snapshot FOR EACH ROW EXECUTE PROCEDURE table_update_notify();

CREATE TRIGGER snapshot_notify_delete
AFTER DELETE ON snapshot FOR EACH ROW EXECUTE PROCEDURE table_update_notify();

CREATE TABLE IF NOT EXISTS snapshot_interval (
  id serial PRIMARY KEY,
  filesystem_name TEXT NOT NULL,
  use_barrier BOOLEAN NOT NULL,
  last_run TIMESTAMP WITH TIME ZONE,
  interval INTERVAL NOT NULL,
  UNIQUE (filesystem_name, interval)
);

CREATE OR REPLACE FUNCTION table_update_notify_snapshot_interval() RETURNS TRIGGER 
  AS $$
    BEGIN
      IF TG_OP = 'INSERT' THEN PERFORM pg_notify(
        'table_update',
        notify_row(TG_OP, TG_TABLE_NAME, json_build_object('id', NEW.id, 'filesystem_name', NEW.filesystem_name, 'use_barrier', NEW.use_barrier, 'last_run', NEW.last_run, 'interval', interval_to_seconds(NEW.interval)))
      );
      ELSEIF TG_OP = 'UPDATE' AND OLD IS DISTINCT FROM NEW THEN PERFORM pg_notify(
        'table_update',
        notify_row(TG_OP, TG_TABLE_NAME, json_build_object('id', NEW.id, 'filesystem_name', NEW.filesystem_name, 'use_barrier', NEW.use_barrier, 'last_run', NEW.last_run, 'interval', interval_to_seconds(NEW.interval)))
      );
      ELSE PERFORM pg_notify(
        'table_update',
        notify_row(TG_OP, TG_TABLE_NAME, json_build_object('id', OLD.id, 'filesystem_name', OLD.filesystem_name, 'use_barrier', OLD.use_barrier, 'last_run', OLD.last_run, 'interval', interval_to_seconds(OLD.interval)))
      );
      END IF;

      RETURN NEW;
    END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS snapshot_interval_notify_update ON snapshot_interval;

DROP TRIGGER IF EXISTS snapshot_interval_notify_insert ON snapshot_interval;

DROP TRIGGER IF EXISTS snapshot_interval_notify_delete ON snapshot_interval;

CREATE TRIGGER snapshot_interval_notify_update
AFTER
UPDATE ON snapshot_interval FOR EACH ROW EXECUTE PROCEDURE table_update_notify_snapshot_interval();

CREATE TRIGGER snapshot_interval_notify_insert
AFTER
INSERT ON snapshot_interval FOR EACH ROW EXECUTE PROCEDURE table_update_notify_snapshot_interval();

CREATE TRIGGER snapshot_interval_notify_delete
AFTER DELETE ON snapshot_interval FOR EACH ROW EXECUTE PROCEDURE table_update_notify_snapshot_interval();

CREATE TYPE snapshot_delete_unit AS ENUM ('percent', 'gibibytes', 'tebibytes');

CREATE TABLE IF NOT EXISTS snapshot_retention (
  id serial PRIMARY KEY,
  filesystem_name TEXT NOT NULL UNIQUE,
  delete_num INT NOT NULL,
  delete_unit snapshot_delete_unit NOT NULL,
  keep_num INT,
  last_run TIMESTAMP WITH TIME ZONE
);

DROP TRIGGER IF EXISTS snapshot_retention_notify_update ON snapshot_retention;

DROP TRIGGER IF EXISTS snapshot_retention_notify_insert ON snapshot_retention;

DROP TRIGGER IF EXISTS snapshot_retention_notify_delete ON snapshot_retention;

CREATE TRIGGER snapshot_retention_notify_update
AFTER
UPDATE ON snapshot_retention FOR EACH ROW EXECUTE PROCEDURE table_update_notify();

CREATE TRIGGER snapshot_retention_notify_insert
AFTER
INSERT ON snapshot_retention FOR EACH ROW EXECUTE PROCEDURE table_update_notify();

CREATE TRIGGER snapshot_retention_notify_delete
AFTER DELETE ON snapshot_retention FOR EACH ROW EXECUTE PROCEDURE table_update_notify();
