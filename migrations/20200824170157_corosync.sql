DO $$ BEGIN
  CREATE TYPE corosync_node_key AS (id non_null_text, NAME non_null_text);
  EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS corosync_cluster (
    id serial PRIMARY KEY,
    corosync_nodes corosync_node_key [ ] UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS corosync_node (
    id corosync_node_key NOT NULL,
    cluster_id INT NOT NULL REFERENCES corosync_cluster (id) ON DELETE CASCADE,
    online boolean NOT NULL,
    standby boolean NOT NULL,
    standby_onfail boolean NOT NULL,
    maintenance boolean NOT NULL,
    pending boolean NOT NULL,
    unclean boolean NOT NULL,
    SHUTDOWN boolean NOT NULL,
    expected_up boolean NOT NULL,
    is_dc boolean NOT NULL,
    resources_running int NOT NULL,
    TYPE text NOT NULL,
    UNIQUE (id, cluster_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS corosync_node_id_idx ON corosync_node (id, cluster_id);

CREATE TABLE IF NOT EXISTS corosync_target_resource (
    id text NOT NULL,
    cluster_id INT NOT NULL REFERENCES corosync_cluster (id) ON DELETE CASCADE,
    resource_agent text NOT NULL,
    role text NOT NULL,
    active BOOLEAN NOT NULL,
    orphaned BOOLEAN NOT NULL,
    managed BOOLEAN NOT NULL,
    failed BOOLEAN NOT NULL,
    failure_ignored BOOLEAN NOT NULL,
    nodes_running_on INT NOT NULL,
    active_node corosync_node_key,
    mount_point text,
    UNIQUE (id, cluster_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS corosync_target_resource_id_idx ON corosync_target_resource (id, cluster_id);

CREATE TABLE IF NOT EXISTS corosync_node_host (
    host_id int NOT NULL REFERENCES host (id),
    corosync_node_id corosync_node_key NOT NULL,
    cluster_id INT NOT NULL,
    FOREIGN KEY (corosync_node_id, cluster_id) REFERENCES corosync_node (id, cluster_id) ON DELETE CASCADE,
    UNIQUE (host_id, corosync_node_id, cluster_id)
);

CREATE TABLE IF NOT EXISTS corosync_target_resource_host (
    host_id INT NOT NULL REFERENCES host (id),
    cluster_id INT NOT NULL,
    corosync_resource_id text NOT NULL,
    FOREIGN KEY (cluster_id, corosync_resource_id) REFERENCES corosync_target_resource (cluster_id, id) ON DELETE CASCADE,
    UNIQUE (host_id, corosync_resource_id, cluster_id)
);

CREATE TABLE IF NOT EXISTS corosync_resource_bans (
    id text NOT NULL,
    cluster_id INT NOT NULL REFERENCES corosync_cluster (id) ON DELETE CASCADE,
    resource text NOT NULL,
    node text NOT NULL,
    weight int NOT NULL,
    master_only boolean NOT NULL,
    UNIQUE (id, cluster_id, resource, node)
);
