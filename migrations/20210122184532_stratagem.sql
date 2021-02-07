CREATE TABLE IF NOT EXISTS stratagemconfiguration (
    id integer NOT NULL,
    state_modified_at timestamp WITH time zone NOT NULL DEFAULT NOW(),
    state character varying(32) NOT NULL,
    "interval" bigint NOT NULL,
    report_duration bigint,
    purge_duration bigint,
    filesystem_id integer NOT NULL REFERENCES filesystem(id)
);

DROP TRIGGER IF EXISTS stratagemconfiguration_notify_update ON stratagemconfiguration;

DROP TRIGGER IF EXISTS stratagemconfiguration_notify_insert ON stratagemconfiguration;

DROP TRIGGER IF EXISTS stratagemconfiguration_notify_delete ON stratagemconfiguration;

CREATE TRIGGER stratagemconfiguration_notify_update
AFTER
UPDATE ON stratagemconfiguration FOR EACH ROW EXECUTE PROCEDURE table_update_notify();

CREATE TRIGGER stratagemconfiguration_notify_insert
AFTER
INSERT ON stratagemconfiguration FOR EACH ROW EXECUTE PROCEDURE table_update_notify();

CREATE TRIGGER stratagemconfiguration_notify_delete
AFTER DELETE ON stratagemconfiguration FOR EACH ROW EXECUTE PROCEDURE table_update_notify();
