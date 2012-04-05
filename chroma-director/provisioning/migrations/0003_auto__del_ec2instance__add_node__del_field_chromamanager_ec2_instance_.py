# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting model 'Ec2Instance'
        db.delete_table('provisioning_ec2instance')

        # Adding model 'Node'
        db.create_table('provisioning_node', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('ec2_id', self.gf('django.db.models.fields.CharField')(unique=True, max_length=10)),
            ('username', self.gf('django.db.models.fields.CharField')(default='root', max_length=25)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=20)),
        ))
        db.send_create_signal('provisioning', ['Node'])

        # Deleting field 'ChromaManager.ec2_instance'
        db.delete_column('provisioning_chromamanager', 'ec2_instance_id')

        # Adding field 'ChromaManager.node'
        db.add_column('provisioning_chromamanager', 'node', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['provisioning.Node'], unique=True, null=True), keep_default=False)

        # Deleting field 'ChromaAppliance.ec2_instance'
        db.delete_column('provisioning_chromaappliance', 'ec2_instance_id')

        # Deleting field 'ChromaAppliance.node_name'
        db.delete_column('provisioning_chromaappliance', 'node_name')

        # Adding field 'ChromaAppliance.node'
        db.add_column('provisioning_chromaappliance', 'node', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['provisioning.Node'], unique=True, null=True), keep_default=False)


    def backwards(self, orm):
        
        # Adding model 'Ec2Instance'
        db.create_table('provisioning_ec2instance', (
            ('ec2_id', self.gf('django.db.models.fields.CharField')(max_length=10, unique=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('provisioning', ['Ec2Instance'])

        # Deleting model 'Node'
        db.delete_table('provisioning_node')

        # Adding field 'ChromaManager.ec2_instance'
        db.add_column('provisioning_chromamanager', 'ec2_instance', self.gf('django.db.models.fields.related.ForeignKey')(default=0, to=orm['provisioning.Ec2Instance'], unique=True), keep_default=False)

        # Deleting field 'ChromaManager.node'
        db.delete_column('provisioning_chromamanager', 'node_id')

        # Adding field 'ChromaAppliance.ec2_instance'
        db.add_column('provisioning_chromaappliance', 'ec2_instance', self.gf('django.db.models.fields.related.ForeignKey')(default=0, to=orm['provisioning.Ec2Instance'], unique=True), keep_default=False)

        # Adding field 'ChromaAppliance.node_name'
        db.add_column('provisioning_chromaappliance', 'node_name', self.gf('django.db.models.fields.CharField')(max_length=20, null=True), keep_default=False)

        # Deleting field 'ChromaAppliance.node'
        db.delete_column('provisioning_chromaappliance', 'node_id')


    models = {
        'provisioning.chromaappliance': {
            'Meta': {'object_name': 'ChromaAppliance'},
            'chroma_manager': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['provisioning.ChromaManager']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'node': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['provisioning.Node']", 'unique': 'True', 'null': 'True'})
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
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'node': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['provisioning.Node']", 'unique': 'True', 'null': 'True'})
        },
        'provisioning.node': {
            'Meta': {'object_name': 'Node'},
            'ec2_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '10'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'username': ('django.db.models.fields.CharField', [], {'default': "'root'", 'max_length': '25'})
        }
    }

    complete_apps = ['provisioning']
