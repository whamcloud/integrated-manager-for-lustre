DROP TRIGGER IF EXISTS target_notify_update ON target;

DROP TRIGGER IF EXISTS target_notify_insert ON target;

DROP TRIGGER IF EXISTS target_notify_delete ON target;

CREATE TRIGGER target_notify_update
AFTER
UPDATE ON target FOR EACH ROW EXECUTE PROCEDURE table_update_notify();

CREATE TRIGGER target_notify_insert
AFTER
INSERT ON target FOR EACH ROW EXECUTE PROCEDURE table_update_notify();

CREATE TRIGGER target_notify_delete
AFTER DELETE ON target FOR EACH ROW EXECUTE PROCEDURE table_update_notify();
