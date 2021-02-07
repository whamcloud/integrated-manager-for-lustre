CREATE TABLE IF NOT EXISTS lustreclientmount (
    id serial PRIMARY KEY,
    state_modified_at timestamp WITH time zone NOT NULL DEFAULT NOW(),
    state character varying(32) NOT NULL,
    filesystem character varying(8) NOT NULL,
    host_id integer NOT NULL,
    mountpoints text [] NOT NULL,
    UNIQUE (host_id, filesystem)
);
