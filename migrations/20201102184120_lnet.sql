CREATE TABLE IF NOT EXISTS lnet (
    id                  serial PRIMARY KEY,
    nid                 text NOT NULL UNIQUE,
    host_id             int NOT NULL,
    net_type            text NOT NULL,
    status              text NOT NULL,
    interfaces          text[] NOT NULL
);
