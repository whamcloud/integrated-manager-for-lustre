CREATE TABLE snapshot (
  filesystem_name TEXT NOT NULL,
  snapshot_name TEXT NOT NULL,
  create_time TIMESTAMP WITH TIME ZONE NOT NULL,
  modify_time TIMESTAMP WITH TIME ZONE NOT NULL,
  snapshot_fsname TEXT NOT NULL,
  mounted BOOLEAN NULL,
  comment TEXT NULL,
  UNIQUE (filesystem_name, snapshot_name)
)
