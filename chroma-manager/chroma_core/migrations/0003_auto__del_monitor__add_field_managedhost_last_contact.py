# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting model 'Monitor'
        db.delete_table('chroma_core_monitor')

        # Adding field 'ManagedHost.last_contact'
        db.add_column('chroma_core_managedhost', 'last_contact', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Adding model 'Monitor'
        db.create_table('chroma_core_monitor', (
            ('host', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.ManagedHost'], unique=True)),
            ('last_success', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('task_id', self.gf('django.db.models.fields.CharField')(default=None, max_length=36, null=True, blank=True)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'], null=True)),
            ('state', self.gf('django.db.models.fields.CharField')(default='idle', max_length=32)),
            ('counter', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('chroma_core', ['Monitor'])

        # Deleting field 'ManagedHost.last_contact'
        db.delete_column('chroma_core_managedhost', 'last_contact')


    models = {
        'chroma_core.alertemail': {
            'Meta': {'object_name': 'AlertEmail'},
            'alerts': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['chroma_core.AlertState']", 'symmetrical': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'chroma_core.alertevent': {
            'Meta': {'object_name': 'AlertEvent', '_ormbases': ['chroma_core.Event']},
            'alert': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.AlertState']"}),
            'event_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Event']", 'unique': 'True', 'primary_key': 'True'}),
            'message_str': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'chroma_core.alertstate': {
            'Meta': {'unique_together': "(('alert_item_type', 'alert_item_id', 'content_type', 'active'),)", 'object_name': 'AlertState'},
            'active': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'alert_item_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'alert_item_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'alertstate_alert_item_type'", 'to': "orm['contenttypes.ContentType']"}),
            'begin': ('django.db.models.fields.DateTimeField', [], {}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'end': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'chroma_core.applyconfparams': {
            'Meta': {'object_name': 'ApplyConfParams', '_ormbases': ['chroma_core.Job']},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'mgs': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedMgs']"})
        },
        'chroma_core.clientconnectevent': {
            'Meta': {'object_name': 'ClientConnectEvent', '_ormbases': ['chroma_core.SyslogEvent']},
            'syslogevent_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.SyslogEvent']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.command': {
            'Meta': {'object_name': 'Command'},
            'cancelled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'complete': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'errored': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'jobs': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['chroma_core.Job']", 'symmetrical': 'False'}),
            'jobs_created': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'message': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'chroma_core.configurelnetjob': {
            'Meta': {'object_name': 'ConfigureLNetJob', '_ormbases': ['chroma_core.Job']},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'lnet_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.LNetConfiguration']"})
        },
        'chroma_core.configuretargetjob': {
            'Meta': {'object_name': 'ConfigureTargetJob', '_ormbases': ['chroma_core.Job']},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedTarget']"})
        },
        'chroma_core.confparam': {
            'Meta': {'object_name': 'ConfParam'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'mgs': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedMgs']"}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '512', 'null': 'True', 'blank': 'True'}),
            'version': ('django.db.models.fields.IntegerField', [], {})
        },
        'chroma_core.detecttargetsjob': {
            'Meta': {'object_name': 'DetectTargetsJob', '_ormbases': ['chroma_core.Job']},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.event': {
            'Meta': {'object_name': 'Event'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'severity': ('django.db.models.fields.IntegerField', [], {})
        },
        'chroma_core.filesystemclientconfparam': {
            'Meta': {'object_name': 'FilesystemClientConfParam', '_ormbases': ['chroma_core.ConfParam']},
            'confparam_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.ConfParam']", 'unique': 'True', 'primary_key': 'True'}),
            'filesystem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedFilesystem']"})
        },
        'chroma_core.filesystemglobalconfparam': {
            'Meta': {'object_name': 'FilesystemGlobalConfParam', '_ormbases': ['chroma_core.ConfParam']},
            'confparam_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.ConfParam']", 'unique': 'True', 'primary_key': 'True'}),
            'filesystem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedFilesystem']"})
        },
        'chroma_core.formattargetjob': {
            'Meta': {'object_name': 'FormatTargetJob', '_ormbases': ['chroma_core.Job']},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedTarget']"})
        },
        'chroma_core.frontlinemetricstore': {
            'Meta': {'object_name': 'FrontLineMetricStore'},
            'complete': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'insert_time': ('django.db.models.fields.DateTimeField', [], {}),
            'metric_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'metric_type': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'value': ('django.db.models.fields.FloatField', [], {})
        },
        'chroma_core.hostcontactalert': {
            'Meta': {'object_name': 'HostContactAlert', '_ormbases': ['chroma_core.AlertState']},
            'alertstate_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.AlertState']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.job': {
            'Meta': {'object_name': 'Job'},
            'cancelled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'errored': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'finished_step': ('django.db.models.fields.PositiveIntegerField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'paused': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'started_step': ('django.db.models.fields.PositiveIntegerField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'default': "'pending'", 'max_length': '16'}),
            'task_id': ('django.db.models.fields.CharField', [], {'max_length': '36', 'null': 'True', 'blank': 'True'}),
            'wait_for': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'wait_for_job'", 'symmetrical': 'False', 'to': "orm['chroma_core.Job']"}),
            'wait_for_completions': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'wait_for_count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'})
        },
        'chroma_core.lastsystemeventsprocessed': {
            'Meta': {'object_name': 'LastSystemeventsProcessed'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'chroma_core.learnevent': {
            'Meta': {'object_name': 'LearnEvent', '_ormbases': ['chroma_core.Event']},
            'event_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Event']", 'unique': 'True', 'primary_key': 'True'}),
            'learned_item_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'learned_item_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"})
        },
        'chroma_core.lnetconfiguration': {
            'Meta': {'object_name': 'LNetConfiguration'},
            'host': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.ManagedHost']", 'unique': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.lnetofflinealert': {
            'Meta': {'object_name': 'LNetOfflineAlert', '_ormbases': ['chroma_core.AlertState']},
            'alertstate_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.AlertState']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.loadlnetjob': {
            'Meta': {'object_name': 'LoadLNetJob', '_ormbases': ['chroma_core.Job']},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.lun': {
            'Meta': {'unique_together': "(('storage_resource', 'not_deleted'),)", 'object_name': 'Lun'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'not_deleted': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'shareable': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'size': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'storage_resource': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.StorageResourceRecord']", 'null': 'True', 'blank': 'True'})
        },
        'chroma_core.lunnode': {
            'Meta': {'unique_together': "(('host', 'path', 'not_deleted'),)", 'object_name': 'LunNode'},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lun': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.Lun']"}),
            'not_deleted': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'path': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'primary': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'storage_resource': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.StorageResourceRecord']", 'null': 'True', 'blank': 'True'}),
            'use': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        'chroma_core.makeavailablefilesystemunavailable': {
            'Meta': {'object_name': 'MakeAvailableFilesystemUnavailable', '_ormbases': ['chroma_core.Job']},
            'filesystem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedFilesystem']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.managedfilesystem': {
            'Meta': {'object_name': 'ManagedFilesystem'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mgs': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedMgs']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '8'}),
            'not_deleted': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.managedhost': {
            'Meta': {'unique_together': "(('address', 'not_deleted'),)", 'object_name': 'ManagedHost'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'agent_token': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'fqdn': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_contact': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'nodename': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'not_deleted': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.managedmdt': {
            'Meta': {'object_name': 'ManagedMdt', '_ormbases': ['chroma_core.ManagedTarget']},
            'filesystem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedFilesystem']"}),
            'managedtarget_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.ManagedTarget']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.managedmgs': {
            'Meta': {'object_name': 'ManagedMgs', '_ormbases': ['chroma_core.ManagedTarget']},
            'conf_param_version': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'conf_param_version_applied': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'managedtarget_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.ManagedTarget']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.managedost': {
            'Meta': {'object_name': 'ManagedOst', '_ormbases': ['chroma_core.ManagedTarget']},
            'filesystem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedFilesystem']"}),
            'managedtarget_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.ManagedTarget']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.managedtarget': {
            'Meta': {'object_name': 'ManagedTarget'},
            'active_mount': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedTargetMount']", 'null': 'True', 'blank': 'True'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'not_deleted': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'})
        },
        'chroma_core.managedtargetmount': {
            'Meta': {'object_name': 'ManagedTargetMount'},
            'block_device': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.LunNode']"}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mount_point': ('django.db.models.fields.CharField', [], {'max_length': '512', 'null': 'True', 'blank': 'True'}),
            'not_deleted': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'primary': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedTarget']"})
        },
        'chroma_core.mdtconfparam': {
            'Meta': {'object_name': 'MdtConfParam', '_ormbases': ['chroma_core.ConfParam']},
            'confparam_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.ConfParam']", 'unique': 'True', 'primary_key': 'True'}),
            'mdt': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedMdt']"})
        },
        'chroma_core.nid': {
            'Meta': {'object_name': 'Nid'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lnet_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.LNetConfiguration']"}),
            'nid_string': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        'chroma_core.opportunisticjob': {
            'Meta': {'object_name': 'OpportunisticJob'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('picklefield.fields.PickledObjectField', [], {}),
            'run': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'run_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        'chroma_core.ostconfparam': {
            'Meta': {'object_name': 'OstConfParam', '_ormbases': ['chroma_core.ConfParam']},
            'confparam_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.ConfParam']", 'unique': 'True', 'primary_key': 'True'}),
            'ost': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedOst']"})
        },
        'chroma_core.registertargetjob': {
            'Meta': {'object_name': 'RegisterTargetJob', '_ormbases': ['chroma_core.Job']},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedTarget']"})
        },
        'chroma_core.removeconfiguredtargetjob': {
            'Meta': {'object_name': 'RemoveConfiguredTargetJob', '_ormbases': ['chroma_core.Job']},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedTarget']"})
        },
        'chroma_core.removefilesystemjob': {
            'Meta': {'object_name': 'RemoveFilesystemJob', '_ormbases': ['chroma_core.Job']},
            'filesystem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedFilesystem']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.removehostjob': {
            'Meta': {'object_name': 'RemoveHostJob', '_ormbases': ['chroma_core.Job']},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.removetargetjob_formatted': {
            'Meta': {'object_name': 'RemoveTargetJob_formatted', '_ormbases': ['chroma_core.Job']},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedTarget']"})
        },
        'chroma_core.removetargetjob_registered': {
            'Meta': {'object_name': 'RemoveTargetJob_registered', '_ormbases': ['chroma_core.Job']},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedTarget']"})
        },
        'chroma_core.removetargetjob_unformatted': {
            'Meta': {'object_name': 'RemoveTargetJob_unformatted', '_ormbases': ['chroma_core.Job']},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedTarget']"})
        },
        'chroma_core.setuphostjob': {
            'Meta': {'object_name': 'SetupHostJob', '_ormbases': ['chroma_core.Job']},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'managed_host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"})
        },
        'chroma_core.simplehistostorebin': {
            'Meta': {'object_name': 'SimpleHistoStoreBin'},
            'bin_idx': ('django.db.models.fields.IntegerField', [], {}),
            'histo_store_time': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.SimpleHistoStoreTime']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'value': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        'chroma_core.simplehistostoretime': {
            'Meta': {'object_name': 'SimpleHistoStoreTime'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'storage_resource_statistic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.StorageResourceStatistic']"}),
            'time': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        'chroma_core.simplescalarstoredatapoint': {
            'Meta': {'object_name': 'SimpleScalarStoreDatapoint'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'storage_resource_statistic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.StorageResourceStatistic']"}),
            'time': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'value': ('django.db.models.fields.BigIntegerField', [], {})
        },
        'chroma_core.startlnetjob': {
            'Meta': {'object_name': 'StartLNetJob', '_ormbases': ['chroma_core.Job']},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.startstoppedfilesystemjob': {
            'Meta': {'object_name': 'StartStoppedFilesystemJob', '_ormbases': ['chroma_core.Job']},
            'filesystem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedFilesystem']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.starttargetjob': {
            'Meta': {'object_name': 'StartTargetJob', '_ormbases': ['chroma_core.Job']},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedTarget']"})
        },
        'chroma_core.startunavailablefilesystemjob': {
            'Meta': {'object_name': 'StartUnavailableFilesystemJob', '_ormbases': ['chroma_core.Job']},
            'filesystem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedFilesystem']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.statelock': {
            'Meta': {'object_name': 'StateLock'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.Job']"}),
            'locked_item_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'locked_item_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'locked_item'", 'to': "orm['contenttypes.ContentType']"})
        },
        'chroma_core.statereadlock': {
            'Meta': {'object_name': 'StateReadLock', '_ormbases': ['chroma_core.StateLock']},
            'statelock_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.StateLock']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.statewritelock': {
            'Meta': {'object_name': 'StateWriteLock', '_ormbases': ['chroma_core.StateLock']},
            'begin_state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'end_state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'statelock_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.StateLock']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.stepresult': {
            'Meta': {'object_name': 'StepResult'},
            'args': ('picklefield.fields.PickledObjectField', [], {}),
            'backtrace': ('django.db.models.fields.TextField', [], {}),
            'console': ('django.db.models.fields.TextField', [], {}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'exception': ('picklefield.fields.PickledObjectField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.Job']"}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'default': "'incomplete'", 'max_length': '32'}),
            'step_count': ('django.db.models.fields.IntegerField', [], {}),
            'step_index': ('django.db.models.fields.IntegerField', [], {}),
            'step_klass': ('picklefield.fields.PickledObjectField', [], {})
        },
        'chroma_core.stoplnetjob': {
            'Meta': {'object_name': 'StopLNetJob', '_ormbases': ['chroma_core.Job']},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.stoptargetjob': {
            'Meta': {'object_name': 'StopTargetJob', '_ormbases': ['chroma_core.Job']},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedTarget']"})
        },
        'chroma_core.stopunavailablefilesystemjob': {
            'Meta': {'object_name': 'StopUnavailableFilesystemJob', '_ormbases': ['chroma_core.Job']},
            'filesystem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedFilesystem']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.storagealertpropagated': {
            'Meta': {'unique_together': "(('storage_resource', 'alert_state'),)", 'object_name': 'StorageAlertPropagated'},
            'alert_state': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.StorageResourceAlert']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'storage_resource': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.StorageResourceRecord']"})
        },
        'chroma_core.storagepluginrecord': {
            'Meta': {'unique_together': "(('module_name',),)", 'object_name': 'StoragePluginRecord'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'module_name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        'chroma_core.storageresourcealert': {
            'Meta': {'object_name': 'StorageResourceAlert', '_ormbases': ['chroma_core.AlertState']},
            'alert_class': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'alertstate_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.AlertState']", 'unique': 'True', 'primary_key': 'True'}),
            'attribute': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'})
        },
        'chroma_core.storageresourceattribute': {
            'Meta': {'unique_together': "(('resource', 'key'),)", 'object_name': 'StorageResourceAttribute'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'resource': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.StorageResourceRecord']"}),
            'value': ('django.db.models.fields.TextField', [], {})
        },
        'chroma_core.storageresourceclass': {
            'Meta': {'unique_together': "(('storage_plugin', 'class_name'),)", 'object_name': 'StorageResourceClass'},
            'class_name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'storage_plugin': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.StoragePluginRecord']"})
        },
        'chroma_core.storageresourceclassstatistic': {
            'Meta': {'unique_together': "(('resource_class', 'name'),)", 'object_name': 'StorageResourceClassStatistic'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'resource_class': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.StorageResourceClass']"})
        },
        'chroma_core.storageresourcelearnevent': {
            'Meta': {'object_name': 'StorageResourceLearnEvent', '_ormbases': ['chroma_core.Event']},
            'event_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Event']", 'unique': 'True', 'primary_key': 'True'}),
            'storage_resource': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.StorageResourceRecord']"})
        },
        'chroma_core.storageresourcerecord': {
            'Meta': {'unique_together': "(('storage_id_str', 'storage_id_scope', 'resource_class'),)", 'object_name': 'StorageResourceRecord'},
            'alias': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'parents': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'resource_parent'", 'symmetrical': 'False', 'to': "orm['chroma_core.StorageResourceRecord']"}),
            'resource_class': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.StorageResourceClass']"}),
            'storage_id_scope': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.StorageResourceRecord']", 'null': 'True', 'blank': 'True'}),
            'storage_id_str': ('django.db.models.fields.CharField', [], {'max_length': '256'})
        },
        'chroma_core.storageresourcestatistic': {
            'Meta': {'unique_together': "(('storage_resource', 'name'),)", 'object_name': 'StorageResourceStatistic'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'sample_period': ('django.db.models.fields.IntegerField', [], {}),
            'storage_resource': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.StorageResourceRecord']"})
        },
        'chroma_core.syslogevent': {
            'Meta': {'object_name': 'SyslogEvent', '_ormbases': ['chroma_core.Event']},
            'event_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Event']", 'unique': 'True', 'primary_key': 'True'}),
            'lustre_pid': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'message_str': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'chroma_core.systemevents': {
            'Meta': {'object_name': 'Systemevents', 'db_table': "u'SystemEvents'"},
            'currusage': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'db_column': "'CurrUsage'", 'blank': 'True'}),
            'customerid': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'db_column': "'CustomerID'", 'blank': 'True'}),
            'devicereportedtime': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'db_column': "'DeviceReportedTime'", 'blank': 'True'}),
            'eventbinarydata': ('django.db.models.fields.TextField', [], {'db_column': "'EventBinaryData'", 'blank': 'True'}),
            'eventcategory': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'db_column': "'EventCategory'", 'blank': 'True'}),
            'eventid': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'db_column': "'EventID'", 'blank': 'True'}),
            'eventlogtype': ('django.db.models.fields.CharField', [], {'max_length': '60', 'db_column': "'EventLogType'", 'blank': 'True'}),
            'eventsource': ('django.db.models.fields.CharField', [], {'max_length': '60', 'db_column': "'EventSource'", 'blank': 'True'}),
            'eventuser': ('django.db.models.fields.CharField', [], {'max_length': '60', 'db_column': "'EventUser'", 'blank': 'True'}),
            'facility': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'db_column': "'Facility'", 'blank': 'True'}),
            'fromhost': ('django.db.models.fields.CharField', [], {'max_length': '60', 'db_column': "'FromHost'", 'blank': 'True'}),
            'genericfilename': ('django.db.models.fields.CharField', [], {'max_length': '60', 'db_column': "'GenericFileName'", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True', 'db_column': "'ID'"}),
            'importance': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'db_column': "'Importance'", 'blank': 'True'}),
            'infounitid': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'db_column': "'InfoUnitID'", 'blank': 'True'}),
            'maxavailable': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'db_column': "'MaxAvailable'", 'blank': 'True'}),
            'maxusage': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'db_column': "'MaxUsage'", 'blank': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {'db_column': "'Message'", 'blank': 'True'}),
            'minusage': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'db_column': "'MinUsage'", 'blank': 'True'}),
            'ntseverity': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'db_column': "'NTSeverity'", 'blank': 'True'}),
            'priority': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'db_column': "'Priority'", 'blank': 'True'}),
            'receivedat': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'db_column': "'ReceivedAt'", 'blank': 'True'}),
            'syslogtag': ('django.db.models.fields.CharField', [], {'max_length': '60', 'db_column': "'SysLogTag'", 'blank': 'True'}),
            'systemid': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'db_column': "'SystemID'", 'blank': 'True'})
        },
        'chroma_core.targetfailoveralert': {
            'Meta': {'object_name': 'TargetFailoverAlert', '_ormbases': ['chroma_core.AlertState']},
            'alertstate_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.AlertState']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.targetofflinealert': {
            'Meta': {'object_name': 'TargetOfflineAlert', '_ormbases': ['chroma_core.AlertState']},
            'alertstate_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.AlertState']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.targetrecoveryalert': {
            'Meta': {'object_name': 'TargetRecoveryAlert', '_ormbases': ['chroma_core.AlertState']},
            'alertstate_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.AlertState']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.targetrecoveryinfo': {
            'Meta': {'object_name': 'TargetRecoveryInfo'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'recovery_status': ('django.db.models.fields.TextField', [], {}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedTarget']"})
        },
        'chroma_core.unloadlnetjob': {
            'Meta': {'object_name': 'UnloadLNetJob', '_ormbases': ['chroma_core.Job']},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['chroma_core']
