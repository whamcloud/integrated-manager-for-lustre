# encoding: utf-8
import datetime
from south.v2 import DataMigration
from r3d import models

updates = [
    (1, 8640, 10000),
    (6, 10080, 60000),
    (30, 8760, 300000),
]
adds = [
    (360, 3600000),
    (8640, 86400000),
]
deletes = [
    (60, 262800),
]

class Migration(DataMigration):

    def forwards(self, orm):
        ids = sorted(set(models.Archive.objects.filter(cdp_per_row=deletes[0][0]).values_list('database_id', flat=True)))
        print 'updating databases', map(int, ids)
        for cdp_per_row, old, new in updates:
            models.Archive.objects.filter(cdp_per_row=cdp_per_row, rows=old).update(rows=new)
        for cdp_per_row, rows in deletes:
            models.Archive.objects.filter(cdp_per_row=cdp_per_row, rows=rows).delete()
        for id in ids:
            db = models.Database.objects.get(id=id)
            for cdp_per_row, rows in adds:
                if not db.archives.filter(cdp_per_row=cdp_per_row):
                    archive = models.Average.objects.create(xff=0.5, database=db, cdp_per_row=cdp_per_row, rows=rows)
                    db.rra_pointers[archive.id] = {'slot': 0, 'wrapped': False}
            db.rebuild_ds_pickle()
            db.rebuild_prep_pickle()
            db.save()

    def backwards(self, orm):
        pass

    models = {
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'r3d.archive': {
            'Meta': {'object_name': 'Archive'},
            'cdp_per_row': ('django.db.models.fields.BigIntegerField', [], {}),
            'cls': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'database': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'archives'", 'to': "orm['r3d.Database']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mod': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'rows': ('django.db.models.fields.BigIntegerField', [], {}),
            'xff': ('r3d.models.SciFloatField', [], {'default': '0.5'})
        },
        'r3d.archiverow': {
            'Meta': {'object_name': 'ArchiveRow'},
            'archive_id': ('django.db.models.fields.IntegerField', [], {}),
            'ds_pickle': ('r3d.models.PickledObjectField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slot': ('django.db.models.fields.BigIntegerField', [], {'default': '0'})
        },
        'r3d.database': {
            'Meta': {'unique_together': "(('content_type', 'object_id'),)", 'object_name': 'Database'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'ds_pickle': ('r3d.models.PickledObjectField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_update': ('django.db.models.fields.BigIntegerField', [], {'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'prep_pickle': ('r3d.models.PickledObjectField', [], {'null': 'True'}),
            'rra_pointers': ('r3d.models.PickledObjectField', [], {'null': 'True'}),
            'start': ('django.db.models.fields.BigIntegerField', [], {'default': '1336610190'}),
            'step': ('django.db.models.fields.BigIntegerField', [], {'default': '300'})
        },
        'r3d.datasource': {
            'Meta': {'unique_together': "(('database', 'name'),)", 'object_name': 'Datasource'},
            'cls': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'database': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'datasources'", 'to': "orm['r3d.Database']"}),
            'heartbeat': ('django.db.models.fields.BigIntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_reading': ('r3d.models.SciFloatField', [], {'null': 'True', 'blank': 'True'}),
            'min_reading': ('r3d.models.SciFloatField', [], {'null': 'True', 'blank': 'True'}),
            'mod': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['r3d']
