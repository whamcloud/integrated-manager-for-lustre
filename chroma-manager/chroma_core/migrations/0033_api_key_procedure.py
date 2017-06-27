# -*- coding: utf-8 -*-
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):
        db.execute("""
CREATE OR REPLACE FUNCTION api_key(
    OUT username text,
    OUT key text
) AS
$func$
BEGIN
    SELECT ta.key, au.username
    INTO key, username
    FROM auth_user as au
    INNER JOIN tastypie_apikey as ta on au.id = ta.user_id 
    WHERE au.username = 'api';
END
$func$ LANGUAGE plpgsql;
        """)

    def backwards(self, orm):
        db.execute("DROP FUNCTION IF EXISTS api_key();")
