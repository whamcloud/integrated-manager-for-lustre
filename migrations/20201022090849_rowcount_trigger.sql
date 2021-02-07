CREATE TABLE rowcount (
    table_name text NOT NULL,
    total_rows bigint,
    PRIMARY KEY (table_name)
);

CREATE OR REPLACE FUNCTION count_rows() RETURNS TRIGGER AS '
    BEGIN
        IF TG_OP = ''INSERT'' THEN
            UPDATE rowcount
            SET total_rows = total_rows + 1
            WHERE table_name = TG_RELNAME;
        ELSIF TG_OP = ''DELETE'' THEN
            UPDATE rowcount
            SET total_rows = total_rows - 1
            WHERE table_name = TG_RELNAME;
        END IF;
        RETURN NULL;
    END;
' LANGUAGE plpgsql;

CREATE TABLE IF NOT EXISTS logmessage (
    id serial PRIMARY KEY,
    datetime TIMESTAMP WITH TIME ZONE NOT NULL,
    fqdn VARCHAR(255) NOT NULL,
    severity SMALLINT NOT NULL,
    facility SMALLINT NOT NULL,
    tag VARCHAR(63) NOT NULL,
    message TEXT NOT NULL,
    message_class SMALLINT NOT NULL
);

BEGIN;

LOCK TABLE logmessage IN SHARE ROW EXCLUSIVE MODE;

CREATE TRIGGER logmessage_countrows
AFTER
INSERT
    OR DELETE ON logmessage FOR EACH ROW EXECUTE PROCEDURE count_rows();

DELETE FROM rowcount
WHERE table_name = 'logmessage';

INSERT INTO rowcount (table_name, total_rows)
VALUES (
        'logmessage',
        (
            SELECT COUNT(*)
            FROM logmessage
        )
    );

COMMIT;
