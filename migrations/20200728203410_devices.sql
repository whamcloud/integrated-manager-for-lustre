-- Create the chroma_core_targets table to store device related information
CREATE TABLE chroma_core_targets (
    state          text,
    name           text,
    active_host_id int,
    host_ids       int[],
    uuid           text,
    mount_path     text
)