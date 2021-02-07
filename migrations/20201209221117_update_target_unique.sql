ALTER TABLE IF EXISTS target DROP CONSTRAINT unique_target_uuid;

DROP INDEX IF EXISTS target_uuid;

CREATE UNIQUE INDEX target_name_uuid ON target (name, uuid);

ALTER TABLE IF EXISTS target
ADD CONSTRAINT unique_target_name_uuid UNIQUE USING INDEX target_name_uuid;
