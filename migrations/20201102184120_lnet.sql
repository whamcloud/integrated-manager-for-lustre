CREATE TABLE IF NOT EXISTS lnet (
    id serial PRIMARY KEY,
    host_id int NOT NULL UNIQUE,
    state text NOT NULL,
    nids int [] NOT NULL
);

DROP TRIGGER IF EXISTS lnet_notify_update ON lnet;

DROP TRIGGER IF EXISTS lnet_notify_insert ON lnet;

DROP TRIGGER IF EXISTS lnet_notify_delete ON lnet;

CREATE TRIGGER lnet_notify_update
AFTER
UPDATE ON lnet FOR EACH ROW EXECUTE PROCEDURE table_update_notify();

CREATE TRIGGER lnet_notify_insert
AFTER
INSERT ON lnet FOR EACH ROW EXECUTE PROCEDURE table_update_notify();

CREATE TRIGGER lnet_notify_delete
AFTER DELETE ON lnet FOR EACH ROW EXECUTE PROCEDURE table_update_notify();

CREATE TABLE IF NOT EXISTS nid (
    id serial PRIMARY KEY,
    net_type text NOT NULL,
    host_id int NOT NULL,
    nid text NOT NULL,
    "status" text NOT NULL,
    interfaces text [] NOT NULL,
    UNIQUE (host_id, nid)
);
