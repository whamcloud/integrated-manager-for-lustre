-- Create the chroma_core_targets table to store device related information
CREATE TABLE chroma_core_targets (
    state          text NOT NULL,
    name           text NOT NULL,
    active_host_id int,
    host_ids       int[],
    uuid           text PRIMARY KEY,
    mount_path     text
)