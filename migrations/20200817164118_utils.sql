-- Make sure we can create composite types with non-null text
DO $$ BEGIN
    CREATE DOMAIN non_null_text AS Text NOT NULL;
    EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Convert an interval to a humantime understandable string
CREATE OR REPLACE FUNCTION interval_to_seconds(interval) RETURNS text
  AS $$ select EXTRACT(EPOCH FROM $1) ||'s' $$
    LANGUAGE SQL
    IMMUTABLE
    RETURNS NULL ON NULL INPUT;

-- Create the akward concatenation of a notify row
CREATE OR REPLACE FUNCTION notify_row(text, text, json) RETURNS text
  AS $$ 
  BEGIN
    RETURN '[ "' || $1 || '", "' || $2 || '", ' || $3 || ']'; 
  END;
  $$ LANGUAGE plpgsql;

-- Covers the 90% case of notifications
CREATE OR REPLACE FUNCTION table_update_notify() RETURNS TRIGGER AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    PERFORM pg_notify('table_update', notify_row(TG_OP, TG_TABLE_NAME, row_to_json(NEW)));
  ELSEIF TG_OP = 'UPDATE' AND OLD IS DISTINCT FROM NEW THEN
    PERFORM pg_notify('table_update', notify_row(TG_OP, TG_TABLE_NAME, row_to_json(NEW)));
  ELSE
    PERFORM pg_notify('table_update', notify_row(TG_OP, TG_TABLE_NAME, row_to_json(OLD)));
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
