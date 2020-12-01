DROP TRIGGER IF EXISTS corosync_resource_notify_update ON target;

DROP TRIGGER IF EXISTS corosync_resource_notify_insert ON target;

DROP TRIGGER IF EXISTS corosync_resource_notify_delete ON target;

CREATE TRIGGER corosync_resource_notify_update
AFTER
UPDATE ON corosync_resource FOR EACH ROW EXECUTE PROCEDURE table_update_notify();

CREATE TRIGGER corosync_resource_notify_insert
AFTER
INSERT ON corosync_resource FOR EACH ROW EXECUTE PROCEDURE table_update_notify();

CREATE TRIGGER corosync_resource_notify_delete
AFTER DELETE ON corosync_resource FOR EACH ROW EXECUTE PROCEDURE table_update_notify();


DROP TRIGGER IF EXISTS corosync_resource_bans_notify_update ON target;

DROP TRIGGER IF EXISTS corosync_resource_bans_notify_insert ON target;

DROP TRIGGER IF EXISTS corosync_resource_bans_notify_delete ON target;

CREATE TRIGGER corosync_resource_bans_notify_update
AFTER
UPDATE ON corosync_resource_bans FOR EACH ROW EXECUTE PROCEDURE table_update_notify();

CREATE TRIGGER corosync_resource_bans_notify_insert
AFTER
INSERT ON corosync_resource_bans FOR EACH ROW EXECUTE PROCEDURE table_update_notify();

CREATE TRIGGER corosync_resource_bans_notify_delete
AFTER DELETE ON corosync_resource_bans FOR EACH ROW EXECUTE PROCEDURE table_update_notify();
