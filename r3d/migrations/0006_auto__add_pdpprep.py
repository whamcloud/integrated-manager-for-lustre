# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'PdpPrep'
        db.create_table('r3d_pdpprep', (
            ('datasource', self.gf('django.db.models.fields.related.OneToOneField')(related_name='prep', unique=True, primary_key=True, to=orm['r3d.Datasource'])),
            ('last_reading', self.gf('r3d.models.SciFloatField')(null=True)),
            ('scratch', self.gf('r3d.models.SciFloatField')(default=0.0, null=True)),
            ('unknown_seconds', self.gf('django.db.models.fields.BigIntegerField')(default=0)),
        ))
        db.send_create_signal('r3d', ['PdpPrep'])

        if not db.dry_run:
            # Migrate relevant DS record fields to new PdpPrep records.
            # We need to use raw to get at the old fields which are no
            # longer defined in the model.
            for ds in orm.Datasource.objects.raw('SELECT * from r3d_datasource'):
                orm.PdpPrep.objects.create(datasource=ds,
                                           last_reading=ds.last_reading,
                                           scratch=ds.pdp_scratch,
                                           unknown_seconds=ds.unknown_seconds)

        # Deleting field 'Datasource.last_reading'
        db.delete_column('r3d_datasource', 'last_reading')

        # Deleting field 'Datasource.pdp_scratch'
        db.delete_column('r3d_datasource', 'pdp_scratch')

        # Deleting field 'Datasource.unknown_seconds'
        db.delete_column('r3d_datasource', 'unknown_seconds')

    def backwards(self, orm):

        # Adding field 'Datasource.last_reading'
        db.add_column('r3d_datasource', 'last_reading', self.gf('r3d.models.SciFloatField')(null=True, blank=True), keep_default=False)

        # Adding field 'Datasource.pdp_scratch'
        db.add_column('r3d_datasource', 'pdp_scratch', self.gf('r3d.models.SciFloatField')(default=0.0, null=True), keep_default=False)

        # Adding field 'Datasource.unknown_seconds'
        db.add_column('r3d_datasource', 'unknown_seconds', self.gf('django.db.models.fields.BigIntegerField')(default=0), keep_default=False)

        if not db.dry_run:
            from django.db import connection, transaction
            cursor = connection.cursor()

            # Migrate PdpPrep data back into Datasource
            for prep in orm['r3d.PdpPrep'].objects.all():
                cursor.execute("UPDATE r3d_datasource SET last_reading = %lf, pdp_scratch = %lf, unknown_seconds = %d WHERE id = %d", [prep.last_reading, prep.scratch, prep.unknown_seconds, prep.datasource_id])
                transaction.commit_unless_managed()
        
        # Deleting model 'PdpPrep'
        db.delete_table('r3d_pdpprep')


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
            'primary': ('r3d.models.SciFloatField', [], {'default': '0.0', 'null': 'True'}),
            'secondary': ('r3d.models.SciFloatField', [], {'default': '0.0', 'null': 'True'}),
            'unknown_pdps': ('django.db.models.fields.BigIntegerField', [], {'default': '0'}),
            'value': ('r3d.models.SciFloatField', [], {'null': 'True'})
        },
        'r3d.database': {
            'Meta': {'unique_together': "(('content_type', 'object_id'),)", 'object_name': 'Database'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_update': ('django.db.models.fields.BigIntegerField', [], {'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'start': ('django.db.models.fields.BigIntegerField', [], {'default': '1320587728'}),
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
        },
        'r3d.pdpprep': {
            'Meta': {'object_name': 'PdpPrep'},
            'datasource': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'prep'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['r3d.Datasource']"}),
            'last_reading': ('r3d.models.SciFloatField', [], {'null': 'True'}),
            'scratch': ('r3d.models.SciFloatField', [], {'default': '0.0', 'null': 'True'}),
            'unknown_seconds': ('django.db.models.fields.BigIntegerField', [], {'default': '0'})
        }
    }

    complete_apps = ['r3d']
