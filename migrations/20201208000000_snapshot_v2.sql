CREATE TABLE IF NOT EXISTS snapshot_policy (
  id serial PRIMARY KEY,
  filesystem TEXT NOT NULL UNIQUE,
  interval INTERVAL NOT NULL,
  barrier BOOLEAN DEFAULT false NOT NULL,
  keep INT NOT NULL CHECK (keep > 0),
  daily INT DEFAULT 0 NOT NULL CHECK (daily >= 0),
  weekly INT DEFAULT 0 NOT NULL CHECK (weekly >= 0),
  monthly INT DEFAULT 0 NOT NULL CHECK (monthly >= 0),
  last_run TIMESTAMP WITH TIME ZONE
);


CREATE OR REPLACE FUNCTION snapshot_policy_func() RETURNS TRIGGER AS $$
DECLARE
  r snapshot_policy;
BEGIN
  IF (TG_OP = 'INSERT') OR (TG_OP = 'UPDATE' AND OLD IS DISTINCT FROM NEW)
  THEN
    r := NEW;
  ELSEIF TG_OP = 'DELETE'
  THEN
    r := OLD;
  ELSE
    r := NULL;
  END IF;

  IF r IS NOT NULL
  THEN
    PERFORM pg_notify(
      'table_update',
      notify_row(TG_OP, TG_TABLE_NAME,
        json_build_object(
          'id', r.id,
          'filesystem', r.filesystem,
          'interval', interval_to_seconds(r.interval),
          'barrier', r.barrier,
          'keep', r.keep,
          'daily', r.daily,
          'weekly', r.weekly,
          'monthly', r.monthly,
          'last_run', r.last_run
      )
    )
  );
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;


DROP TRIGGER IF EXISTS snapshot_policy_notify_update ON snapshot_policy;
CREATE TRIGGER snapshot_policy_notify_update AFTER UPDATE ON snapshot_policy
FOR EACH ROW EXECUTE PROCEDURE snapshot_policy_func();

DROP TRIGGER IF EXISTS snapshot_policy_notify_insert ON snapshot_policy;
CREATE TRIGGER snapshot_policy_notify_insert AFTER INSERT ON snapshot_policy
FOR EACH ROW EXECUTE PROCEDURE snapshot_policy_func();

DROP TRIGGER IF EXISTS snapshot_policy_notify_delete ON snapshot_policy;
CREATE TRIGGER snapshot_policy_notify_delete AFTER DELETE ON snapshot_policy
FOR EACH ROW EXECUTE PROCEDURE snapshot_policy_func();


DROP TABLE IF EXISTS snapshot_interval CASCADE;
DROP TABLE IF EXISTS snapshot_retention CASCADE;
DROP FUNCTION IF EXISTS table_update_notify_snapshot_interval() CASCADE;
DROP TYPE IF EXISTS snapshot_reserve_unit CASCADE;
