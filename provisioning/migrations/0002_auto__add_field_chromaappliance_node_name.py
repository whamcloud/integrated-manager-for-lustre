# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'ChromaAppliance.node_name'
        db.add_column('provisioning_chromaappliance', 'node_name', self.gf('django.db.models.fields.CharField')(max_length=20, null=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'ChromaAppliance.node_name'
        db.delete_column('provisioning_chromaappliance', 'node_name')


    models = {
        'provisioning.chromaappliance': {
            'Meta': {'object_name': 'ChromaAppliance'},
            'chroma_manager': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['provisioning.ChromaManager']"}),
            'ec2_instance': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['provisioning.Ec2Instance']", 'unique': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'node_name': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True'})
        },
        'provisioning.chromafilesystem': {
            'Meta': {'object_name': 'ChromaFilesystem'},
            'chroma_id': ('django.db.models.fields.IntegerField', [], {}),
            'chroma_manager': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['provisioning.ChromaManager']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '8'})
        },
        'provisioning.chromamanager': {
            'Meta': {'object_name': 'ChromaManager'},
            'ec2_instance': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['provisioning.Ec2Instance']", 'unique': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'provisioning.ec2instance': {
            'Meta': {'object_name': 'Ec2Instance'},
            'ec2_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '10'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['provisioning']
