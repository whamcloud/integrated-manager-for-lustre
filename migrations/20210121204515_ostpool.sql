CREATE TABLE IF NOT EXISTS ostpool (
    id serial PRIMARY KEY,
    name character varying(15) NOT NULL,
    filesystem_id integer NOT NULL REFERENCES filesystem(id),
    UNIQUE (name, filesystem_id)
);

DROP TRIGGER IF EXISTS ostpool_notify_update ON ostpool;

DROP TRIGGER IF EXISTS ostpool_notify_insert ON ostpool;

DROP TRIGGER IF EXISTS ostpool_notify_delete ON ostpool;

CREATE TRIGGER ostpool_notify_update
AFTER
UPDATE ON ostpool FOR EACH ROW EXECUTE PROCEDURE table_update_notify();

CREATE TRIGGER ostpool_notify_insert
AFTER
INSERT ON ostpool FOR EACH ROW EXECUTE PROCEDURE table_update_notify();

CREATE TRIGGER ostpool_notify_delete
AFTER DELETE ON ostpool FOR EACH ROW EXECUTE PROCEDURE table_update_notify();

CREATE TABLE IF NOT EXISTS ostpool_osts (
    id serial PRIMARY KEY,
    ostpool_id integer NOT NULL REFERENCES ostpool(id),
    ost_id integer NOT NULL REFERENCES target(id),
    UNIQUE (ostpool_id, ost_id)
);

DROP TRIGGER IF EXISTS ostpool_osts_notify_update ON ostpool_osts;

DROP TRIGGER IF EXISTS ostpool_osts_notify_insert ON ostpool_osts;

DROP TRIGGER IF EXISTS ostpool_osts_notify_delete ON ostpool_osts;

CREATE TRIGGER ostpool_osts_notify_update
AFTER
UPDATE ON ostpool_osts FOR EACH ROW EXECUTE PROCEDURE table_update_notify();

CREATE TRIGGER ostpool_osts_notify_insert
AFTER
INSERT ON ostpool_osts FOR EACH ROW EXECUTE PROCEDURE table_update_notify();

CREATE TRIGGER ostpool_osts_notify_delete
AFTER DELETE ON ostpool_osts FOR EACH ROW EXECUTE PROCEDURE table_update_notify();
