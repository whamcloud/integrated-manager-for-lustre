CREATE TABLE IF NOT EXISTS lnet (
    id                  serial PRIMARY KEY,
    host_id             int NOT NULL UNIQUE,
    state               text NOT NULL,
    nids                int[] NOT NULL
);

CREATE TABLE IF NOT EXISTS nid (
    id serial PRIMARY KEY,
    net_type text NOT NULL,
    host_id int NOT NULL UNIQUE,
    nid text NOT NULL,
    status text NOT NULL,
    interfaces text[] NOT NULL,
    UNIQUE (host_id, nid)
);
