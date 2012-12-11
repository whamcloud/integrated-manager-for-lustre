#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from django.db.models.signals import post_syncdb
import r3d.models


def archiverow_custom_pk(sender, **kwargs):
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

post_syncdb.connect(archiverow_custom_pk, sender=r3d.models)
