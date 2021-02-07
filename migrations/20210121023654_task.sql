DO $$ BEGIN CREATE TYPE lustre_fid AS (seq bigint, oid integer, ver integer);

EXCEPTION
WHEN duplicate_object THEN NULL;

END $$;

CREATE TABLE IF NOT EXISTS task (
    id serial PRIMARY KEY,
    name character varying(128) NOT NULL UNIQUE,
    START timestamp WITH time zone NOT NULL,
    finish timestamp WITH time zone,
    state character varying(16) NOT NULL,
    fids_total bigint NOT NULL,
    fids_completed bigint NOT NULL,
    fids_failed bigint NOT NULL,
    data_transfered bigint NOT NULL,
    single_runner boolean NOT NULL,
    keep_failed boolean NOT NULL,
    actions text [] NOT NULL,
    args jsonb NOT NULL,
    filesystem_id integer NOT NULL,
    running_on_id integer REFERENCES host(id)
);

CREATE TABLE IF NOT EXISTS fidtaskqueue (
    id serial PRIMARY KEY,
    fid lustre_fid NOT NULL,
    data jsonb NOT NULL,
    task_id integer NOT NULL REFERENCES task(id)
);

CREATE TABLE IF NOT EXISTS fidtaskerror (
    id serial PRIMARY KEY,
    fid lustre_fid NOT NULL,
    data jsonb NOT NULL,
    errno smallint NOT NULL,
    task_id integer NOT NULL REFERENCES task(id),
    CONSTRAINT fidtaskerror_errno_check CHECK ((errno >= 0))
);
