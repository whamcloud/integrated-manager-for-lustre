CREATE TABLE target (
    state          text NOT NULL,
    name           text NOT NULL,
    active_host_id int NULL,
    host_ids       int[] NOT NULL,
    filesystems    text[] NOT NULL,
    uuid           text PRIMARY KEY,
    mount_path     text NULL
)
