CREATE TABLE IF NOT EXISTS input_document (
    id                serial PRIMARY KEY,
    document          JSONB NOT NULL,
    creation_time     timestamp WITH time zone NOT NULL DEFAULT now()
);
