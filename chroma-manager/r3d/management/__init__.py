#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from django.db.models.signals import post_syncdb
import r3d.models


def _mysql_archiverow_custom_pk(sender, **kwargs):
    from django.db import connection
    cursor = connection.cursor()

    # This isn't perfect, but it should prevent us from attempting to
    # mangle the PK on already-mangled DBs.
    cursor.execute("SHOW INDEX from r3d_archiverow")
    indexed_columns = [r[4] for r in cursor.fetchall() or ()]
    if 'archive_id' in indexed_columns and 'slot' in indexed_columns:
        return

    # Remove the Django-created pk on id and add a custom multi-column
    # pk on archive_id, slot.  This is necessary for the performance
    # aspect of pk indexes as well as correct ON DUPLICATE KEY UPDATE
    # behavior.
    cursor.execute("ALTER TABLE r3d_archiverow CHANGE id id INT(11) NOT NULL DEFAULT 0; ALTER TABLE r3d_archiverow DROP PRIMARY KEY; ALTER TABLE r3d_archiverow ADD PRIMARY KEY (archive_id, slot)")


def _pgsql_archiverow_custom_pk(sender, **kwargs):
    from django.db import connection
    cursor = connection.cursor()

    # This isn't perfect, but it should prevent us from attempting to
    # mangle the PK on already-mangled DBs.
    cursor.execute("""
        SELECT  c.oid,
                c.relname
        FROM    pg_catalog.pg_class c
        LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relname ~ '^(r3d_archiverow)$'
        AND pg_catalog.pg_table_is_visible(c.oid)
        ORDER BY 2;
    """)
    oid = cursor.fetchone()[0]
    cursor.execute("""
        SELECT  c2.relname,
                i.indisprimary,
                i.indisunique,
                i.indisclustered,
                i.indisvalid,
                pg_catalog.pg_get_indexdef(i.indexrelid, 0, true),
                c2.reltablespace
        FROM    pg_catalog.pg_class c,
                pg_catalog.pg_class c2,
                pg_catalog.pg_index i
        WHERE c.oid = '%s' AND c.oid = i.indrelid AND i.indexrelid = c2.oid
        ORDER BY i.indisprimary DESC, i.indisunique DESC, c2.relname;
    """ % oid)
    if 'archive_id' in cursor.fetchone()[5]:
        return

    # Remove the Django-created pk on id and add a custom multi-column
    # pk on archive_id, slot.  This is necessary for the performance
    # aspect of pk indexes as well as correct ON DUPLICATE KEY UPDATE
    # behavior.
    cursor.execute("ALTER TABLE r3d_archiverow DROP CONSTRAINT r3d_archiverow_pkey; ALTER TABLE r3d_archiverow ALTER COLUMN id SET DEFAULT 0; ALTER TABLE r3d_archiverow ADD PRIMARY KEY (archive_id, slot)")


def archiverow_custom_pk(sender, **kwargs):
    from django.db import connection
    if 'mysql' in connection.settings_dict['ENGINE']:
        _mysql_archiverow_custom_pk(sender, **kwargs)
    elif 'postgres' in connection.settings_dict['ENGINE']:
        _pgsql_archiverow_custom_pk(sender, **kwargs)
    else:
        raise RuntimeError("Unsupported DB: %s" % connection.settings_dict['ENGINE'])

post_syncdb.connect(archiverow_custom_pk, sender=r3d.models)
