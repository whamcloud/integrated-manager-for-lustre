# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Ec2Instance'
        db.create_table('provisioning_ec2instance', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('ec2_id', self.gf('django.db.models.fields.CharField')(unique=True, max_length=10)),
        ))
        db.send_create_signal('provisioning', ['Ec2Instance'])

        # Adding model 'ChromaManager'
        db.create_table('provisioning_chromamanager', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('ec2_instance', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['provisioning.Ec2Instance'], unique=True)),
        ))
        db.send_create_signal('provisioning', ['ChromaManager'])

        # Adding model 'ChromaAppliance'
        db.create_table('provisioning_chromaappliance', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('ec2_instance', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['provisioning.Ec2Instance'], unique=True)),
            ('chroma_manager', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['provisioning.ChromaManager'])),
        ))
        db.send_create_signal('provisioning', ['ChromaAppliance'])

        # Adding model 'ChromaFilesystem'
        db.create_table('provisioning_chromafilesystem', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=8)),
            ('chroma_manager', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['provisioning.ChromaManager'])),
            ('chroma_id', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal('provisioning', ['ChromaFilesystem'])


    def backwards(self, orm):
        
        # Deleting model 'Ec2Instance'
        db.delete_table('provisioning_ec2instance')

        # Deleting model 'ChromaManager'
        db.delete_table('provisioning_chromamanager')

        # Deleting model 'ChromaAppliance'
        db.delete_table('provisioning_chromaappliance')

        # Deleting model 'ChromaFilesystem'
        db.delete_table('provisioning_chromafilesystem')


    models = {
        'provisioning.chromaappliance': {
            'Meta': {'object_name': 'ChromaAppliance'},
            'chroma_manager': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['provisioning.ChromaManager']"}),
            'ec2_instance': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['provisioning.Ec2Instance']", 'unique': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
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
