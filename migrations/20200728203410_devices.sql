CREATE TABLE IF NOT EXISTS device (
    id serial PRIMARY KEY,
    fqdn VARCHAR(255) NOT NULL UNIQUE,
    devices JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS target (
    state text NOT NULL,
    name text NOT NULL,
    active_host_id int NULL,
    host_ids int [] NOT NULL,
    filesystems text [] NOT NULL,
    uuid text PRIMARY KEY,
    mount_path text NULL
);
