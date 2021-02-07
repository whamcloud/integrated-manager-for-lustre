CREATE TABLE IF NOT EXISTS host (
    id serial PRIMARY KEY,
    machine_id text NOT NULL UNIQUE,
    fqdn text NOT NULL UNIQUE,
    boot_time TIMESTAMP WITH TIME ZONE NOT NULL,
    state text NOT NULL
);

DROP TRIGGER IF EXISTS host_notify_update ON host;

DROP TRIGGER IF EXISTS host_notify_insert ON host;

DROP TRIGGER IF EXISTS host_notify_delete ON host;

CREATE TRIGGER host_notify_update
AFTER
UPDATE ON host FOR EACH ROW EXECUTE PROCEDURE table_update_notify();

CREATE TRIGGER host_notify_insert
AFTER
INSERT ON host FOR EACH ROW EXECUTE PROCEDURE table_update_notify();

CREATE TRIGGER host_notify_delete
AFTER DELETE ON host FOR EACH ROW EXECUTE PROCEDURE table_update_notify();
