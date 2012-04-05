

from django.db import models
from django.contrib.contenttypes.models import ContentType

from chroma_core.models.utils import WorkaroundGenericForeignKey, WorkaroundDateTimeField


class FrontLineMetricStore(models.Model):
    """Fast simple metrics store.  Should be backed by MEMORY engine."""
    content_type = models.ForeignKey(ContentType, null=True)
    object_id = models.PositiveIntegerField(null=True)
    content_object = WorkaroundGenericForeignKey('content_type', 'object_id')
    insert_time = WorkaroundDateTimeField()
    metric_name = models.CharField(max_length=255)
    metric_type = models.CharField(max_length=64)
    value = models.FloatField()
    complete = models.BooleanField(default=False, db_index=True)

    class Meta:
        app_label = 'chroma_core'

    @classmethod
    def store_update(cls, ct, o_id, update_time, update):
        from datetime import datetime as dt
        from django.db import connection, transaction
        cursor = connection.cursor()

        names = update.keys()
        for name in names:
            data = update[name]
            params = [dt.fromtimestamp(update_time), ct.id, o_id, name]
            try:
                params.append(data['type'])
                params.append(data['value'])
            except TypeError:
                # FIXME: do we really want to default this, or raise?
                params.append('Counter')
                params.append(data)

            # Use this to signal that all of the metrics for this update
            # have been inserted.
            params.append(1 if name == names[-1] else 0)

            # Bypass the ORM for this -- we don't care about instantiating
            # objects from these inserts.
            sql = "INSERT into chroma_core_frontlinemetricstore (insert_time, content_type_id, object_id, metric_name, metric_type, value, complete) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            cursor.execute(sql, params)
            transaction.commit_unless_managed()
