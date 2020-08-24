CREATE TABLE corosync_node (
    id text NOT NULL,
    name text NOT NULL,
    online boolean NOT NULL,
    standby boolean NOT NULL,
    standby_onfail boolean NOT NULL,
    maintenance boolean NOT NULL,
    pending boolean NOT NULL,
    unclean boolean NOT NULL,
    shutdown boolean NOT NULL,
    expected_up boolean NOT NULL,
    is_dc boolean NOT NULL,
    resources_running int NOT NULL,
    type text NOT NULL,
    UNIQUE (id, name)
);

CREATE UNIQUE INDEX id_idx ON corosync_node (id, name);

CREATE TABLE corosync_node_managed_host (
    host_id int NOT NULL REFERENCES chroma_core_managedhost (id),
    corosync_node_id text,
    corosync_node_name text,
    FOREIGN KEY (corosync_node_id, corosync_node_name) REFERENCES corosync_node (id, name) ON DELETE CASCADE,
    UNIQUE (host_id, corosync_node_id, corosync_node_name)
);