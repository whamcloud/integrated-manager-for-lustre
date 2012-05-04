# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'ArchiveRow'
        db.create_table('r3d_archiverow', (
            ('id', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('archive_id', self.gf('django.db.models.fields.IntegerField')()),
            ('slot', self.gf('django.db.models.fields.BigIntegerField')(default=0)),
            ('ds_pickle', self.gf('r3d.models.PickledObjectField')(null=True)),
        ))
        db.execute("ALTER TABLE r3d_archiverow ADD PRIMARY KEY (archive_id, slot)")
        db.send_create_signal('r3d', ['ArchiveRow'])


    def backwards(self, orm):
        
        # Deleting model 'ArchiveRow'
        db.delete_table('r3d_archiverow')


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
            'archive_id': ('django.db.models.fields.IntegerField', [], {}),
            'ds_pickle': ('r3d.models.PickledObjectField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slot': ('django.db.models.fields.BigIntegerField', [], {'default': '0'})
        },
        'r3d.cdp': {
            'Meta': {'unique_together': "(['archive', 'datasource', 'slot'],)", 'object_name': 'CDP'},
            'archive': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'cdps'", 'to': "orm['r3d.Archive']"}),
            'datasource': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'cdps'", 'to': "orm['r3d.Datasource']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'row_id': ('django.db.models.fields.BigIntegerField', [], {'default': '0'}),
            'slot': ('django.db.models.fields.BigIntegerField', [], {'default': '0'}),
            'value': ('r3d.models.SciFloatField', [], {'null': 'True'})
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
            'start': ('django.db.models.fields.BigIntegerField', [], {'default': '1336113141'}),
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
