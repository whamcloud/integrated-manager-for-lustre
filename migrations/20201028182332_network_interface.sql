CREATE TYPE lnd_network_type AS ENUM ('tcp', 'o2ib');

CREATE TABLE IF NOT EXISTS network_interface (
    mac_address    text PRIMARY KEY,
    name           text NOT NULL,
    inet4_address  inet[] NOT NULL,
    inet6_address  inet[] NOT NULL,
    lnd_type       lnd_network_type,
    state_up       boolean NOT NULL,
    host_id        int NOT NULL
);
