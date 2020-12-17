DROP TYPE IF EXISTS lnet_state;
CREATE TYPE lnet_state AS ENUM ('up', 'down', 'unloaded');

ALTER TABLE IF EXISTS lnet ALTER COLUMN state TYPE lnet_state USING state::lnet_state;

ALTER TABLE IF EXISTS lnet DROP CONSTRAINT IF EXISTS host_fkey;
ALTER TABLE IF EXISTS lnet
    ADD CONSTRAINT host_fkey
    FOREIGN KEY (host_id)
    REFERENCES chroma_core_managedhost(id)
    ON DELETE CASCADE;

ALTER TABLE IF EXISTS nid DROP CONSTRAINT IF EXISTS host_fkey;
ALTER TABLE IF EXISTS nid
    ADD CONSTRAINT host_fkey
    FOREIGN KEY (host_id)
    REFERENCES chroma_core_managedhost(id)
    ON DELETE CASCADE;
