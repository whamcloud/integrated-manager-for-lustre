CREATE TABLE IF NOT EXISTS filesystem (
    id serial PRIMARY KEY,
    state_modified_at timestamp WITH time zone NOT NULL DEFAULT NOW(),
    state character varying(32) NOT NULL,
    name character varying(8) NOT NULL,
    mdt_next_index integer NOT NULL,
    ost_next_index integer NOT NULL,
    mgs_id integer NOT NULL,
    mdt_ids int [] NOT NULL,
    ost_ids int [] NOT NULL,
    UNIQUE (name, mgs_id)
);

DROP TRIGGER IF EXISTS filesystem_notify_update ON filesystem;

DROP TRIGGER IF EXISTS filesystem_notify_insert ON filesystem;

DROP TRIGGER IF EXISTS filesystem_notify_delete ON filesystem;

CREATE TRIGGER filesystem_notify_update
AFTER
UPDATE ON filesystem FOR EACH ROW EXECUTE PROCEDURE table_update_notify();

CREATE TRIGGER filesystem_notify_insert
AFTER
INSERT ON filesystem FOR EACH ROW EXECUTE PROCEDURE table_update_notify();

CREATE TRIGGER filesystem_notify_delete
AFTER DELETE ON filesystem FOR EACH ROW EXECUTE PROCEDURE table_update_notify();
