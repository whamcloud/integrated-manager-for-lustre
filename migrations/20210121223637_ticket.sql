CREATE TABLE IF NOT EXISTS ticket (
    id serial PRIMARY KEY,
    state_modified_at timestamp WITH time zone NOT NULL,
    state character varying(32) NOT NULL,
    ha_label character varying(64),
    name character varying(64) NOT NULL,
    resource_controlled boolean NOT NULL,
    cluster_id integer
);

CREATE TABLE IF NOT EXISTS masterticket (
    ticket_ptr_id integer NOT NULL PRIMARY KEY REFERENCES ticket(id),
    mgs_id integer NOT NULL REFERENCES target(id)
);

CREATE TABLE IF NOT EXISTS filesystemticket (
    ticket_ptr_id integer PRIMARY KEY REFERENCES ticket(id),
    filesystem_id integer NOT NULL REFERENCES filesystem(id)
);
