CREATE TYPE machine_state AS ENUM (
    'pending',
    'progress',
    'failed',
    'succeeded',
    'cancelled'
);

CREATE TYPE step_state as ENUM (
    'progress',
    'failed',
    'cancelled'
);

CREATE TABLE IF NOT EXISTS command (
    id serial PRIMARY KEY,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    end_time TIMESTAMP WITH TIME ZONE,
    state machine_state NOT NULL DEFAULT 'pending',
    message TEXT NOT NULL,
    jobs int[] NOT NULL DEFAULT array[]::int[]
);

CREATE TABLE IF NOT EXISTS job (
    id serial PRIMARY KEY,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    end_time TIMESTAMP WITH TIME ZONE,
    state machine_state NOT NULL DEFAULT 'pending',
    command_id INT NOT NULL REFERENCES command (id) ON DELETE CASCADE,
    job jsonb NOT NULL,
    wait_for_jobs int[] NOT NULL,
    locked_records jsonb[]
);

CREATE TABLE IF NOT EXISTS step (
    id serial PRIMARY KEY,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    job_id INT NOT NULL REFERENCES job (id) ON DELETE CASCADE,
    result jsonb,
    logs text NOT NULL DEFAULT '',
    state step_state NOT NULL DEFAULT 'progress'
)