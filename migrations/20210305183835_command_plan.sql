DROP TYPE IF EXISTS state;

CREATE TYPE state AS ENUM (
    'pending',
    'running',
    'completed',
    'canceled',
    'failed'
);

CREATE TABLE IF NOT EXISTS command_plan (
    id serial PRIMARY KEY,
    plan JSONB NOT NULL,
    state state NOT NULL DEFAULT 'pending'
);
