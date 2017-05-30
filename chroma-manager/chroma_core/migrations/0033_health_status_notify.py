# -*- coding: utf-8 -*-
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):
        db.execute("""
CREATE OR REPLACE FUNCTION table_update_notify() RETURNS trigger AS $$
DECLARE
  id bigint;
BEGIN
  IF TG_OP = 'INSERT' OR TG_OP = 'UPDATE' THEN
    id = NEW.id;
  ELSE
    id = OLD.id;
  END IF;

  PERFORM pg_notify('table_update', TG_OP || ',' || TG_TABLE_NAME || ',' || id);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER chroma_core_alertstate_notify_update
ON chroma_core_alertstate;

DROP TRIGGER chroma_core_alertstate_notify_insert
ON chroma_core_alertstate;

DROP TRIGGER chroma_core_alertstate_notify_delete
ON chroma_core_alertstate;

CREATE TRIGGER chroma_core_alertstate_notify_update
AFTER UPDATE ON chroma_core_alertstate
FOR EACH ROW EXECUTE PROCEDURE table_update_notify();

CREATE TRIGGER chroma_core_alertstate_notify_insert
AFTER INSERT ON chroma_core_alertstate
FOR EACH ROW EXECUTE PROCEDURE table_update_notify();

CREATE TRIGGER chroma_core_alertstate_notify_delete
AFTER DELETE ON chroma_core_alertstate
FOR EACH ROW EXECUTE PROCEDURE table_update_notify();
""")

    def backwards(self, orm):
        db.execute("""
DROP TRIGGER chroma_core_alertstate_notify_update
ON chroma_core_alertstate;

DROP TRIGGER chroma_core_alertstate_notify_insert
ON chroma_core_alertstate;

DROP TRIGGER chroma_core_alertstate_notify_delete
ON chroma_core_alertstate;

DROP FUNCTION IF EXISTS table_update_notify();
""")
