# -*- coding: utf-8 -*-
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):
        db.execute("""
CREATE OR REPLACE FUNCTION health_status(
    OUT health text
    ,OUT num_alerts int
) AS
$func$
DECLARE
    sev integer;
BEGIN
    SELECT severity
    INTO sev
    FROM chroma_core_alertstate a
    WHERE COALESCE(a.dismissed, FALSE) = FALSE
    AND a.active = TRUE
    AND a.severity IN (30, 40)
    ORDER BY a.severity DESC LIMIT 1;

    IF sev = 30 THEN
        health := 'WARNING';
    ELSIF sev = 40 THEN
        health := 'ERROR';
    ELSE
        health := 'GOOD';
    END IF;

    SELECT COUNT(*)
    INTO num_alerts
    FROM chroma_core_alertstate a
    WHERE COALESCE(a.dismissed, FALSE) = FALSE
    AND a.severity IN (30, 40)
    AND a.active = TRUE;
END
$func$ LANGUAGE plpgsql;
        """)

    def backwards(self, orm):
        db.execute("DROP FUNCTION IF EXISTS health_status();")
