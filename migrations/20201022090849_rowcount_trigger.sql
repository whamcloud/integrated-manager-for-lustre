CREATE TABLE rowcount (
    table_name  text NOT NULL,
    total_rows  bigint,
    PRIMARY KEY (table_name));

CREATE OR REPLACE FUNCTION count_rows()
RETURNS TRIGGER AS
'
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

BEGIN;
    LOCK TABLE chroma_core_logmessage IN SHARE ROW EXCLUSIVE MODE;

    CREATE TRIGGER chroma_core_logmessage_countrows
        AFTER INSERT OR DELETE ON chroma_core_logmessage
        FOR EACH ROW EXECUTE PROCEDURE count_rows();

    DELETE FROM rowcount WHERE table_name = 'chroma_core_logmessage';

    INSERT INTO rowcount (table_name, total_rows)
    VALUES  ('chroma_core_logmessage',  (SELECT COUNT(*) FROM chroma_core_logmessage));

COMMIT;
