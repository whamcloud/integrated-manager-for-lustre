# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Removing unique constraint on 'CdpPrep', fields ['archive', 'datasource']
        db.delete_unique('r3d_cdpprep', ['archive_id', 'datasource_id'])

        # Deleting model 'CdpPrep'
        db.delete_table('r3d_cdpprep')

        # Deleting model 'PdpPrep'
        db.delete_table('r3d_pdpprep')

        # Adding field 'Database.ds_pickle'
        db.add_column('r3d_database', 'ds_pickle', self.gf('r3d.models.PickledObjectField')(null=True), keep_default=False)

        # Adding field 'Database.prep_pickle'
        db.add_column('r3d_database', 'prep_pickle', self.gf('r3d.models.PickledObjectField')(null=True), keep_default=False)


    def backwards(self, orm):
        
        # Adding model 'CdpPrep'
        db.create_table('r3d_cdpprep', (
            ('value', self.gf('r3d.models.SciFloatField')(null=True)),
            ('primary', self.gf('r3d.models.SciFloatField')(default=0.0, null=True)),
            ('datasource', self.gf('django.db.models.fields.related.ForeignKey')(related_name='preps', to=orm['r3d.Datasource'])),
            ('secondary', self.gf('r3d.models.SciFloatField')(default=0.0, null=True)),
            ('archive', self.gf('django.db.models.fields.related.ForeignKey')(related_name='preps', to=orm['r3d.Archive'])),
            ('unknown_pdps', self.gf('django.db.models.fields.BigIntegerField')(default=0)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('r3d', ['CdpPrep'])

        # Adding unique constraint on 'CdpPrep', fields ['archive', 'datasource']
        db.create_unique('r3d_cdpprep', ['archive_id', 'datasource_id'])

        # Adding model 'PdpPrep'
        db.create_table('r3d_pdpprep', (
            ('scratch', self.gf('r3d.models.SciFloatField')(default=0.0, null=True)),
            ('unknown_seconds', self.gf('django.db.models.fields.BigIntegerField')(default=0)),
            ('datasource', self.gf('django.db.models.fields.related.OneToOneField')(related_name='prep', unique=True, primary_key=True, to=orm['r3d.Datasource'])),
            ('last_reading', self.gf('r3d.models.SciFloatField')(null=True)),
        ))
        db.send_create_signal('r3d', ['PdpPrep'])

        # Deleting field 'Database.ds_pickle'
        db.delete_column('r3d_database', 'ds_pickle')

        # Deleting field 'Database.prep_pickle'
        db.delete_column('r3d_database', 'prep_pickle')


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
            'current_row': ('django.db.models.fields.BigIntegerField', [], {'default': '0'}),
            'database': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'archives'", 'to': "orm['r3d.Database']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mod': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'rows': ('django.db.models.fields.BigIntegerField', [], {}),
            'xff': ('r3d.models.SciFloatField', [], {'default': '0.5'})
        },
        'r3d.cdp': {
            'Meta': {'object_name': 'CDP'},
            'archive': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'cdps'", 'to': "orm['r3d.Archive']"}),
            'datasource': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'cdps'", 'to': "orm['r3d.Datasource']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
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
            'start': ('django.db.models.fields.BigIntegerField', [], {'default': '1334526046'}),
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
