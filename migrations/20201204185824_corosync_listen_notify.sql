DROP TRIGGER IF EXISTS corosync_resource_notify_update ON corosync_resource;

DROP TRIGGER IF EXISTS corosync_resource_notify_insert ON corosync_resource;

DROP TRIGGER IF EXISTS corosync_resource_notify_delete ON corosync_resource;

CREATE TRIGGER corosync_resource_notify_update
AFTER
UPDATE ON corosync_resource FOR EACH ROW EXECUTE PROCEDURE table_update_notify();

CREATE TRIGGER corosync_resource_notify_insert
AFTER
INSERT ON corosync_resource FOR EACH ROW EXECUTE PROCEDURE table_update_notify();

CREATE TRIGGER corosync_resource_notify_delete
AFTER DELETE ON corosync_resource FOR EACH ROW EXECUTE PROCEDURE table_update_notify();


DROP TRIGGER IF EXISTS corosync_resource_bans_notify_update ON corosync_resource_bans;

DROP TRIGGER IF EXISTS corosync_resource_bans_notify_insert ON corosync_resource_bans;

DROP TRIGGER IF EXISTS corosync_resource_bans_notify_delete ON corosync_resource_bans;

CREATE TRIGGER corosync_resource_bans_notify_update
AFTER
UPDATE ON corosync_resource_bans FOR EACH ROW EXECUTE PROCEDURE table_update_notify();

CREATE TRIGGER corosync_resource_bans_notify_insert
AFTER
INSERT ON corosync_resource_bans FOR EACH ROW EXECUTE PROCEDURE table_update_notify();

CREATE TRIGGER corosync_resource_bans_notify_delete
AFTER DELETE ON corosync_resource_bans FOR EACH ROW EXECUTE PROCEDURE table_update_notify();
