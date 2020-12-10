DROP TYPE IF EXISTS lnet_state;
CREATE TYPE lnet_state AS ENUM ('up', 'down', 'unloaded');

ALTER TABLE IF EXISTS lnet ALTER COLUMN state TYPE lnet_state USING state::lnet_state;
