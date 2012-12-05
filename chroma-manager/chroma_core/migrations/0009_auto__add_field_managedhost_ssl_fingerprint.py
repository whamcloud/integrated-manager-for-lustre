# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'ManagedHost.ssl_fingerprint'
        db.add_column('chroma_core_managedhost', 'ssl_fingerprint',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=64),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'ManagedHost.ssl_fingerprint'
        db.delete_column('chroma_core_managedhost', 'ssl_fingerprint')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
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
            'Meta': {'unique_together': "(('alert_item_type', 'alert_item_id', 'alert_type', 'active'),)", 'object_name': 'AlertState'},
            'active': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'alert_item_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'alert_item_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'alertstate_alert_item_type'", 'to': "orm['contenttypes.ContentType']"}),
            'alert_type': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'begin': ('django.db.models.fields.DateTimeField', [], {}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'dismissed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'end': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'chroma_core.alertsubscription': {
            'Meta': {'object_name': 'AlertSubscription'},
            'alert_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'alert_subscriptions'", 'to': "orm['auth.User']"})
        },
        'chroma_core.applyconfparams': {
            'Meta': {'object_name': 'ApplyConfParams', '_ormbases': ['chroma_core.Job']},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'mgs': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedMgs']"})
        },
        'chroma_core.clientconnectevent': {
            'Meta': {'object_name': 'ClientConnectEvent', '_ormbases': ['chroma_core.Event']},
            'event_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Event']", 'unique': 'True', 'primary_key': 'True'}),
            'lustre_pid': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'message_str': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'chroma_core.command': {
            'Meta': {'object_name': 'Command'},
            'cancelled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'complete': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'errored': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'jobs': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['chroma_core.Job']", 'symmetrical': 'False'}),
            'message': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'chroma_core.configurelnetjob': {
            'Meta': {'object_name': 'ConfigureLNetJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'lnet_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.LNetConfiguration']"}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.configuretargetjob': {
            'Meta': {'object_name': 'ConfigureTargetJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
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
            'host_ids': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.enablelnetjob': {
            'Meta': {'object_name': 'EnableLNetJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'managed_host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.event': {
            'Meta': {'object_name': 'Event'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'severity': ('django.db.models.fields.IntegerField', [], {})
        },
        'chroma_core.failbacktargetjob': {
            'Meta': {'object_name': 'FailbackTargetJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedTarget']"})
        },
        'chroma_core.failovertargetjob': {
            'Meta': {'object_name': 'FailoverTargetJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedTarget']"})
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
        'chroma_core.forceremovehostjob': {
            'Meta': {'object_name': 'ForceRemoveHostJob'},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.forgetfilesystemjob': {
            'Meta': {'object_name': 'ForgetFilesystemJob'},
            'filesystem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedFilesystem']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.forgettargetjob': {
            'Meta': {'object_name': 'ForgetTargetJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedTarget']"})
        },
        'chroma_core.formattargetjob': {
            'Meta': {'object_name': 'FormatTargetJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedTarget']"})
        },
        'chroma_core.getlnetstatejob': {
            'Meta': {'object_name': 'GetLNetStateJob', '_ormbases': ['chroma_core.Job']},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'})
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
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'locks_json': ('django.db.models.fields.TextField', [], {}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'default': "'pending'", 'max_length': '16'}),
            'wait_for_json': ('django.db.models.fields.TextField', [], {})
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
            'immutable_state': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'state_modified_at': ('django.db.models.fields.DateTimeField', [], {})
        },
        'chroma_core.lnetnidschangedalert': {
            'Meta': {'object_name': 'LNetNidsChangedAlert', '_ormbases': ['chroma_core.AlertState']},
            'alertstate_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.AlertState']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.lnetofflinealert': {
            'Meta': {'object_name': 'LNetOfflineAlert', '_ormbases': ['chroma_core.AlertState']},
            'alertstate_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.AlertState']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.loadlnetjob': {
            'Meta': {'object_name': 'LoadLNetJob'},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.logmessage': {
            'Meta': {'object_name': 'LogMessage'},
            'datetime': ('django.db.models.fields.DateTimeField', [], {}),
            'facility': ('django.db.models.fields.SmallIntegerField', [], {}),
            'fqdn': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'message_class': ('django.db.models.fields.SmallIntegerField', [], {}),
            'severity': ('django.db.models.fields.SmallIntegerField', [], {}),
            'tag': ('django.db.models.fields.CharField', [], {'max_length': '63'})
        },
        'chroma_core.makeavailablefilesystemunavailable': {
            'Meta': {'object_name': 'MakeAvailableFilesystemUnavailable'},
            'filesystem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedFilesystem']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.managedfilesystem': {
            'Meta': {'object_name': 'ManagedFilesystem'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'immutable_state': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'mdt_next_index': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'mgs': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedMgs']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '8'}),
            'not_deleted': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'ost_next_index': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'state_modified_at': ('django.db.models.fields.DateTimeField', [], {})
        },
        'chroma_core.managedhost': {
            'Meta': {'unique_together': "(('address', 'not_deleted'),)", 'object_name': 'ManagedHost'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'fqdn': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'immutable_state': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'nodename': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'not_deleted': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'ssl_fingerprint': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'state_modified_at': ('django.db.models.fields.DateTimeField', [], {})
        },
        'chroma_core.managedmdt': {
            'Meta': {'object_name': 'ManagedMdt', '_ormbases': ['chroma_core.ManagedTarget']},
            'filesystem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedFilesystem']"}),
            'index': ('django.db.models.fields.IntegerField', [], {}),
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
            'index': ('django.db.models.fields.IntegerField', [], {}),
            'managedtarget_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.ManagedTarget']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.managedtarget': {
            'Meta': {'object_name': 'ManagedTarget'},
            'active_mount': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedTargetMount']", 'null': 'True', 'blank': 'True'}),
            'bytes_per_inode': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'ha_label': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'immutable_state': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'inode_count': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'inode_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'not_deleted': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'state_modified_at': ('django.db.models.fields.DateTimeField', [], {}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'volume': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.Volume']"})
        },
        'chroma_core.managedtargetmount': {
            'Meta': {'object_name': 'ManagedTargetMount'},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mount_point': ('django.db.models.fields.CharField', [], {'max_length': '512', 'null': 'True', 'blank': 'True'}),
            'not_deleted': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'primary': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedTarget']"}),
            'volume_node': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.VolumeNode']"})
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
        'chroma_core.ostconfparam': {
            'Meta': {'object_name': 'OstConfParam', '_ormbases': ['chroma_core.ConfParam']},
            'confparam_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.ConfParam']", 'unique': 'True', 'primary_key': 'True'}),
            'ost': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedOst']"})
        },
        'chroma_core.registertargetjob': {
            'Meta': {'object_name': 'RegisterTargetJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedTarget']"})
        },
        'chroma_core.relearnnidsjob': {
            'Meta': {'object_name': 'RelearnNidsJob', '_ormbases': ['chroma_core.Job']},
            'host_ids': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.removeconfiguredtargetjob': {
            'Meta': {'object_name': 'RemoveConfiguredTargetJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedTarget']"})
        },
        'chroma_core.removefilesystemjob': {
            'Meta': {'object_name': 'RemoveFilesystemJob'},
            'filesystem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedFilesystem']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.removehostjob': {
            'Meta': {'object_name': 'RemoveHostJob'},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.removetargetjob': {
            'Meta': {'object_name': 'RemoveTargetJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedTarget']"})
        },
        'chroma_core.removeunconfiguredhostjob': {
            'Meta': {'object_name': 'RemoveUnconfiguredHostJob'},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.setuphostjob': {
            'Meta': {'object_name': 'SetupHostJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'managed_host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
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
        'chroma_core.startlnetjob': {
            'Meta': {'object_name': 'StartLNetJob'},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.startstoppedfilesystemjob': {
            'Meta': {'object_name': 'StartStoppedFilesystemJob'},
            'filesystem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedFilesystem']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.starttargetjob': {
            'Meta': {'object_name': 'StartTargetJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedTarget']"})
        },
        'chroma_core.startunavailablefilesystemjob': {
            'Meta': {'object_name': 'StartUnavailableFilesystemJob'},
            'filesystem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedFilesystem']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.stepresult': {
            'Meta': {'object_name': 'StepResult'},
            'args': ('picklefield.fields.PickledObjectField', [], {}),
            'backtrace': ('django.db.models.fields.TextField', [], {}),
            'console': ('django.db.models.fields.TextField', [], {}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.Job']"}),
            'log': ('django.db.models.fields.TextField', [], {}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'default': "'incomplete'", 'max_length': '32'}),
            'step_count': ('django.db.models.fields.IntegerField', [], {}),
            'step_index': ('django.db.models.fields.IntegerField', [], {}),
            'step_klass': ('picklefield.fields.PickledObjectField', [], {})
        },
        'chroma_core.stoplnetjob': {
            'Meta': {'object_name': 'StopLNetJob'},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.stoptargetjob': {
            'Meta': {'object_name': 'StopTargetJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedTarget']"})
        },
        'chroma_core.stopunavailablefilesystemjob': {
            'Meta': {'object_name': 'StopUnavailableFilesystemJob'},
            'filesystem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedFilesystem']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
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
            'internal': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'module_name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        'chroma_core.storageresourcealert': {
            'Meta': {'object_name': 'StorageResourceAlert', '_ormbases': ['chroma_core.AlertState']},
            'alert_class': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'alertstate_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.AlertState']", 'unique': 'True', 'primary_key': 'True'}),
            'attribute': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'})
        },
        'chroma_core.storageresourceattributereference': {
            'Meta': {'object_name': 'StorageResourceAttributeReference'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'resource': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.StorageResourceRecord']"}),
            'value': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'value_resource'", 'null': 'True', 'on_delete': 'models.PROTECT', 'to': "orm['chroma_core.StorageResourceRecord']"})
        },
        'chroma_core.storageresourceattributeserialized': {
            'Meta': {'object_name': 'StorageResourceAttributeSerialized'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'resource': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.StorageResourceRecord']"}),
            'value': ('django.db.models.fields.TextField', [], {})
        },
        'chroma_core.storageresourceclass': {
            'Meta': {'unique_together': "(('storage_plugin', 'class_name'),)", 'object_name': 'StorageResourceClass'},
            'class_name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'storage_plugin': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.StoragePluginRecord']", 'on_delete': 'models.PROTECT'}),
            'user_creatable': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
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
            'storage_resource': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.StorageResourceRecord']", 'on_delete': 'models.PROTECT'})
        },
        'chroma_core.storageresourceoffline': {
            'Meta': {'object_name': 'StorageResourceOffline', '_ormbases': ['chroma_core.AlertState']},
            'alertstate_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.AlertState']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.storageresourcerecord': {
            'Meta': {'unique_together': "(('storage_id_str', 'storage_id_scope', 'resource_class'),)", 'object_name': 'StorageResourceRecord'},
            'alias': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'parents': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'resource_parent'", 'symmetrical': 'False', 'to': "orm['chroma_core.StorageResourceRecord']"}),
            'reported_by': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'resource_reported_by'", 'symmetrical': 'False', 'to': "orm['chroma_core.StorageResourceRecord']"}),
            'resource_class': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.StorageResourceClass']", 'on_delete': 'models.PROTECT'}),
            'storage_id_scope': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.StorageResourceRecord']", 'null': 'True', 'on_delete': 'models.PROTECT', 'blank': 'True'}),
            'storage_id_str': ('django.db.models.fields.CharField', [], {'max_length': '256'})
        },
        'chroma_core.storageresourcestatistic': {
            'Meta': {'unique_together': "(('storage_resource', 'name'),)", 'object_name': 'StorageResourceStatistic'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'sample_period': ('django.db.models.fields.IntegerField', [], {}),
            'storage_resource': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.StorageResourceRecord']", 'on_delete': 'models.PROTECT'})
        },
        'chroma_core.syslogevent': {
            'Meta': {'object_name': 'SyslogEvent', '_ormbases': ['chroma_core.Event']},
            'event_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Event']", 'unique': 'True', 'primary_key': 'True'}),
            'lustre_pid': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'message_str': ('django.db.models.fields.CharField', [], {'max_length': '512'})
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
            'Meta': {'object_name': 'UnloadLNetJob'},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.updatenidsjob': {
            'Meta': {'object_name': 'UpdateNidsJob', '_ormbases': ['chroma_core.Job']},
            'host_ids': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.volume': {
            'Meta': {'unique_together': "(('storage_resource', 'not_deleted'),)", 'object_name': 'Volume'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'not_deleted': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'size': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'storage_resource': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.StorageResourceRecord']", 'null': 'True', 'on_delete': 'models.PROTECT', 'blank': 'True'})
        },
        'chroma_core.volumenode': {
            'Meta': {'unique_together': "(('host', 'path', 'not_deleted'),)", 'object_name': 'VolumeNode'},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'not_deleted': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'path': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'primary': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'storage_resource': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.StorageResourceRecord']", 'null': 'True', 'blank': 'True'}),
            'use': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'volume': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.Volume']"})
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