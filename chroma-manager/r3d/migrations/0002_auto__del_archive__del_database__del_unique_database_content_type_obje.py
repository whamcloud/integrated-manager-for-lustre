# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Removing unique constraint on 'Datasource', fields ['database', 'name']
        db.delete_unique('r3d_datasource', ['database_id', 'name'])

        # Removing unique constraint on 'Database', fields ['content_type', 'object_id']
        db.delete_unique('r3d_database', ['content_type_id', 'object_id'])

        # Deleting model 'Archive'
        db.delete_table('r3d_archive')

        # Deleting model 'Database'
        db.delete_table('r3d_database')

        # Deleting model 'Datasource'
        db.delete_table('r3d_datasource')

        # Deleting model 'ArchiveRow'
        db.delete_table('r3d_archiverow')


    def backwards(self, orm):
        # Adding model 'Archive'
        db.create_table('r3d_archive', (
            ('cdp_per_row', self.gf('django.db.models.fields.BigIntegerField')()),
            ('database', self.gf('django.db.models.fields.related.ForeignKey')(related_name='archives', to=orm['r3d.Database'])),
            ('rows', self.gf('django.db.models.fields.BigIntegerField')()),
            ('mod', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('xff', self.gf('r3d.models.SciFloatField')(default=0.5)),
            ('cls', self.gf('django.db.models.fields.CharField')(max_length=30)),
        ))
        db.send_create_signal('r3d', ['Archive'])

        # Adding model 'Database'
        db.create_table('r3d_database', (
            ('prep_pickle', self.gf('r3d.models.PickledObjectField')(null=True)),
            ('step', self.gf('django.db.models.fields.BigIntegerField')(default=300)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'], null=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255, unique=True)),
            ('rra_pointers', self.gf('r3d.models.PickledObjectField')(null=True)),
            ('ds_pickle', self.gf('r3d.models.PickledObjectField')(null=True)),
            ('object_id', self.gf('django.db.models.fields.PositiveIntegerField')(null=True)),
            ('last_update', self.gf('django.db.models.fields.BigIntegerField')(blank=True)),
            ('start', self.gf('django.db.models.fields.BigIntegerField')(default=1339681242)),
        ))
        db.send_create_signal('r3d', ['Database'])

        # Adding unique constraint on 'Database', fields ['content_type', 'object_id']
        db.create_unique('r3d_database', ['content_type_id', 'object_id'])

        # Adding model 'Datasource'
        db.create_table('r3d_datasource', (
            ('max_reading', self.gf('r3d.models.SciFloatField')(null=True, blank=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('min_reading', self.gf('r3d.models.SciFloatField')(null=True, blank=True)),
            ('database', self.gf('django.db.models.fields.related.ForeignKey')(related_name='datasources', to=orm['r3d.Database'])),
            ('heartbeat', self.gf('django.db.models.fields.BigIntegerField')()),
            ('mod', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('cls', self.gf('django.db.models.fields.CharField')(max_length=30)),
        ))
        db.send_create_signal('r3d', ['Datasource'])

        # Adding unique constraint on 'Datasource', fields ['database', 'name']
        db.create_unique('r3d_datasource', ['database_id', 'name'])

        # Adding model 'ArchiveRow'
        db.create_table('r3d_archiverow', (
            ('archive_id', self.gf('django.db.models.fields.IntegerField')()),
            ('slot', self.gf('django.db.models.fields.BigIntegerField')(default=0)),
            ('ds_pickle', self.gf('r3d.models.PickledObjectField')(null=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('r3d', ['ArchiveRow'])


    models = {
        
    }

    complete_apps = ['r3d']