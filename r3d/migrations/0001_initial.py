## Copyright 2011 Whamcloud, Inc.
## Authors: Michael MacDonald <mjmac@whamcloud.com>

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
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('start', self.gf('django.db.models.fields.BigIntegerField')(default=1317186508)),
            ('step', self.gf('django.db.models.fields.BigIntegerField')(default=300)),
            ('last_update', self.gf('django.db.models.fields.BigIntegerField')(blank=True)),
        ))
        db.send_create_signal('r3d', ['Database'])

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
            ('last_reading', self.gf('r3d.models.SciFloatField')(null=True, blank=True)),
            ('pdp_scratch', self.gf('r3d.models.SciFloatField')(default=0.0, null=True)),
            ('unknown_seconds', self.gf('django.db.models.fields.BigIntegerField')(default=0)),
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
            ('current_row', self.gf('django.db.models.fields.BigIntegerField')(default=0)),
        ))
        db.send_create_signal('r3d', ['Archive'])

        # Adding model 'CDP'
        db.create_table('r3d_cdp', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('archive', self.gf('django.db.models.fields.related.ForeignKey')(related_name='cdps', to=orm['r3d.Archive'])),
            ('datasource', self.gf('django.db.models.fields.related.ForeignKey')(related_name='cdps', to=orm['r3d.Datasource'])),
            ('value', self.gf('r3d.models.SciFloatField')(null=True)),
        ))
        db.send_create_signal('r3d', ['CDP'])

        # Adding model 'CdpPrep'
        db.create_table('r3d_cdpprep', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('archive', self.gf('django.db.models.fields.related.ForeignKey')(related_name='preps', to=orm['r3d.Archive'])),
            ('datasource', self.gf('django.db.models.fields.related.ForeignKey')(related_name='preps', to=orm['r3d.Datasource'])),
            ('value', self.gf('r3d.models.SciFloatField')(null=True)),
            ('primary', self.gf('r3d.models.SciFloatField')(null=True)),
            ('secondary', self.gf('r3d.models.SciFloatField')(null=True)),
            ('unknown_pdps', self.gf('django.db.models.fields.BigIntegerField')(default=0)),
        ))
        db.send_create_signal('r3d', ['CdpPrep'])

        # Adding unique constraint on 'CdpPrep', fields ['archive', 'datasource']
        db.create_unique('r3d_cdpprep', ['archive_id', 'datasource_id'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'CdpPrep', fields ['archive', 'datasource']
        db.delete_unique('r3d_cdpprep', ['archive_id', 'datasource_id'])

        # Removing unique constraint on 'Datasource', fields ['database', 'name']
        db.delete_unique('r3d_datasource', ['database_id', 'name'])

        # Deleting model 'Database'
        db.delete_table('r3d_database')

        # Deleting model 'Datasource'
        db.delete_table('r3d_datasource')

        # Deleting model 'Archive'
        db.delete_table('r3d_archive')

        # Deleting model 'CDP'
        db.delete_table('r3d_cdp')

        # Deleting model 'CdpPrep'
        db.delete_table('r3d_cdpprep')


    models = {
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
        'r3d.cdpprep': {
            'Meta': {'unique_together': "(('archive', 'datasource'),)", 'object_name': 'CdpPrep'},
            'archive': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'preps'", 'to': "orm['r3d.Archive']"}),
            'datasource': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'preps'", 'to': "orm['r3d.Datasource']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'primary': ('r3d.models.SciFloatField', [], {'null': 'True'}),
            'secondary': ('r3d.models.SciFloatField', [], {'null': 'True'}),
            'unknown_pdps': ('django.db.models.fields.BigIntegerField', [], {'default': '0'}),
            'value': ('r3d.models.SciFloatField', [], {'null': 'True'})
        },
        'r3d.database': {
            'Meta': {'object_name': 'Database'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_update': ('django.db.models.fields.BigIntegerField', [], {'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'start': ('django.db.models.fields.BigIntegerField', [], {'default': '1317186508'}),
            'step': ('django.db.models.fields.BigIntegerField', [], {'default': '300'})
        },
        'r3d.datasource': {
            'Meta': {'unique_together': "(('database', 'name'),)", 'object_name': 'Datasource'},
            'cls': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'database': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'datasources'", 'to': "orm['r3d.Database']"}),
            'heartbeat': ('django.db.models.fields.BigIntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_reading': ('r3d.models.SciFloatField', [], {'null': 'True', 'blank': 'True'}),
            'max_reading': ('r3d.models.SciFloatField', [], {'null': 'True', 'blank': 'True'}),
            'min_reading': ('r3d.models.SciFloatField', [], {'null': 'True', 'blank': 'True'}),
            'mod': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'pdp_scratch': ('r3d.models.SciFloatField', [], {'default': '0.0', 'null': 'True'}),
            'unknown_seconds': ('django.db.models.fields.BigIntegerField', [], {'default': '0'})
        }
    }

    complete_apps = ['r3d']
