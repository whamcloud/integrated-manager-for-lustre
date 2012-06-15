# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Database'
        db.create_table('r3d_database', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
            ('start', self.gf('django.db.models.fields.BigIntegerField')(default=1339681242)),
            ('step', self.gf('django.db.models.fields.BigIntegerField')(default=300)),
            ('last_update', self.gf('django.db.models.fields.BigIntegerField')(blank=True)),
            ('ds_pickle', self.gf('r3d.models.PickledObjectField')(null=True)),
            ('prep_pickle', self.gf('r3d.models.PickledObjectField')(null=True)),
            ('rra_pointers', self.gf('r3d.models.PickledObjectField')(null=True)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'], null=True)),
            ('object_id', self.gf('django.db.models.fields.PositiveIntegerField')(null=True)),
        ))
        db.send_create_signal('r3d', ['Database'])

        # Adding unique constraint on 'Database', fields ['content_type', 'object_id']
        db.create_unique('r3d_database', ['content_type_id', 'object_id'])

        # Adding model 'Datasource'
        db.create_table('r3d_datasource', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('mod', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('cls', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('database', self.gf('django.db.models.fields.related.ForeignKey')(related_name='datasources', to=orm['r3d.Database'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('heartbeat', self.gf('django.db.models.fields.BigIntegerField')()),
            ('min_reading', self.gf('r3d.models.SciFloatField')(null=True, blank=True)),
            ('max_reading', self.gf('r3d.models.SciFloatField')(null=True, blank=True)),
        ))
        db.send_create_signal('r3d', ['Datasource'])

        # Adding unique constraint on 'Datasource', fields ['database', 'name']
        db.create_unique('r3d_datasource', ['database_id', 'name'])

        # Adding model 'Archive'
        db.create_table('r3d_archive', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('mod', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('cls', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('database', self.gf('django.db.models.fields.related.ForeignKey')(related_name='archives', to=orm['r3d.Database'])),
            ('xff', self.gf('r3d.models.SciFloatField')(default=0.5)),
            ('cdp_per_row', self.gf('django.db.models.fields.BigIntegerField')()),
            ('rows', self.gf('django.db.models.fields.BigIntegerField')()),
        ))
        db.send_create_signal('r3d', ['Archive'])

        # Adding model 'ArchiveRow'
        db.create_table('r3d_archiverow', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('archive_id', self.gf('django.db.models.fields.IntegerField')()),
            ('slot', self.gf('django.db.models.fields.BigIntegerField')(default=0)),
            ('ds_pickle', self.gf('r3d.models.PickledObjectField')(null=True)),
        ))
        db.send_create_signal('r3d', ['ArchiveRow'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'Datasource', fields ['database', 'name']
        db.delete_unique('r3d_datasource', ['database_id', 'name'])

        # Removing unique constraint on 'Database', fields ['content_type', 'object_id']
        db.delete_unique('r3d_database', ['content_type_id', 'object_id'])

        # Deleting model 'Database'
        db.delete_table('r3d_database')

        # Deleting model 'Datasource'
        db.delete_table('r3d_datasource')

        # Deleting model 'Archive'
        db.delete_table('r3d_archive')

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
            'start': ('django.db.models.fields.BigIntegerField', [], {'default': '1339681242'}),
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
