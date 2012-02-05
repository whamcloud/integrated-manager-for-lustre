# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Removing unique constraint on 'LunNode', fields ['path', 'host']
        db.delete_unique('configure_lunnode', ['path', 'host_id'])

        # Adding field 'LunNode.not_deleted'
        db.add_column('configure_lunnode', 'not_deleted', self.gf('django.db.models.fields.NullBooleanField')(default=True, null=True, blank=True), keep_default=False)

        # Adding unique constraint on 'LunNode', fields ['path', 'host', 'not_deleted']
        db.create_unique('configure_lunnode', ['path', 'host_id', 'not_deleted'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'LunNode', fields ['path', 'host', 'not_deleted']
        db.delete_unique('configure_lunnode', ['path', 'host_id', 'not_deleted'])

        # Deleting field 'LunNode.not_deleted'
        db.delete_column('configure_lunnode', 'not_deleted')

        # Adding unique constraint on 'LunNode', fields ['path', 'host']
        db.create_unique('configure_lunnode', ['path', 'host_id'])


    models = {
        'configure.applyconfparams': {
            'Meta': {'object_name': 'ApplyConfParams', '_ormbases': ['configure.Job']},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['configure.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'mgs': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.ManagedMgs']"})
        },
        'configure.configurelnetjob': {
            'Meta': {'object_name': 'ConfigureLNetJob', '_ormbases': ['configure.Job']},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['configure.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'lnet_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.LNetConfiguration']"})
        },
        'configure.configuretargetmountjob': {
            'Meta': {'object_name': 'ConfigureTargetMountJob', '_ormbases': ['configure.Job']},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['configure.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'target_mount': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.ManagedTargetMount']"})
        },
        'configure.confparam': {
            'Meta': {'object_name': 'ConfParam'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'mgs': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.ManagedMgs']"}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '512', 'null': 'True', 'blank': 'True'}),
            'version': ('django.db.models.fields.IntegerField', [], {})
        },
        'configure.detecttargetsjob': {
            'Meta': {'object_name': 'DetectTargetsJob', '_ormbases': ['configure.Job']},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['configure.Job']", 'unique': 'True', 'primary_key': 'True'})
        },
        'configure.filesystemclientconfparam': {
            'Meta': {'object_name': 'FilesystemClientConfParam', '_ormbases': ['configure.ConfParam']},
            'confparam_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['configure.ConfParam']", 'unique': 'True', 'primary_key': 'True'}),
            'filesystem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.ManagedFilesystem']"})
        },
        'configure.filesystemglobalconfparam': {
            'Meta': {'object_name': 'FilesystemGlobalConfParam', '_ormbases': ['configure.ConfParam']},
            'confparam_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['configure.ConfParam']", 'unique': 'True', 'primary_key': 'True'}),
            'filesystem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.ManagedFilesystem']"})
        },
        'configure.formattargetjob': {
            'Meta': {'object_name': 'FormatTargetJob', '_ormbases': ['configure.Job']},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['configure.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.ManagedTarget']"})
        },
        'configure.job': {
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
            'wait_for': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'wait_for_job'", 'symmetrical': 'False', 'to': "orm['configure.Job']"}),
            'wait_for_completions': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'wait_for_count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'})
        },
        'configure.lnetconfiguration': {
            'Meta': {'object_name': 'LNetConfiguration'},
            'host': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['configure.ManagedHost']", 'unique': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'configure.loadlnetjob': {
            'Meta': {'object_name': 'LoadLNetJob', '_ormbases': ['configure.Job']},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.ManagedHost']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['configure.Job']", 'unique': 'True', 'primary_key': 'True'})
        },
        'configure.lun': {
            'Meta': {'unique_together': "(('storage_resource',),)", 'object_name': 'Lun'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'shareable': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'size': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'storage_resource': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.StorageResourceRecord']", 'null': 'True', 'blank': 'True'})
        },
        'configure.lunnode': {
            'Meta': {'unique_together': "(('host', 'path', 'not_deleted'),)", 'object_name': 'LunNode'},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.ManagedHost']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lun': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.Lun']"}),
            'not_deleted': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'path': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'primary': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'storage_resource': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.StorageResourceRecord']", 'null': 'True', 'blank': 'True'}),
            'use': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        'configure.makeavailablefilesystemunavailable': {
            'Meta': {'object_name': 'MakeAvailableFilesystemUnavailable', '_ormbases': ['configure.Job']},
            'filesystem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.ManagedFilesystem']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['configure.Job']", 'unique': 'True', 'primary_key': 'True'})
        },
        'configure.managedfilesystem': {
            'Meta': {'object_name': 'ManagedFilesystem'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mgs': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.ManagedMgs']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '8'}),
            'not_deleted': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'configure.managedhost': {
            'Meta': {'unique_together': "(('address', 'not_deleted'),)", 'object_name': 'ManagedHost'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'fqdn': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'not_deleted': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'configure.managedmdt': {
            'Meta': {'object_name': 'ManagedMdt', '_ormbases': ['configure.ManagedTarget']},
            'filesystem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.ManagedFilesystem']"}),
            'managedtarget_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['configure.ManagedTarget']", 'unique': 'True', 'primary_key': 'True'})
        },
        'configure.managedmgs': {
            'Meta': {'object_name': 'ManagedMgs', '_ormbases': ['configure.ManagedTarget']},
            'conf_param_version': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'conf_param_version_applied': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'managedtarget_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['configure.ManagedTarget']", 'unique': 'True', 'primary_key': 'True'})
        },
        'configure.managedost': {
            'Meta': {'object_name': 'ManagedOst', '_ormbases': ['configure.ManagedTarget']},
            'filesystem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.ManagedFilesystem']"}),
            'managedtarget_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['configure.ManagedTarget']", 'unique': 'True', 'primary_key': 'True'})
        },
        'configure.managedtarget': {
            'Meta': {'object_name': 'ManagedTarget'},
            'active_mount': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.ManagedTargetMount']", 'null': 'True', 'blank': 'True'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'not_deleted': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'})
        },
        'configure.managedtargetmount': {
            'Meta': {'object_name': 'ManagedTargetMount'},
            'block_device': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.LunNode']"}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.ManagedHost']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mount_point': ('django.db.models.fields.CharField', [], {'max_length': '512', 'null': 'True', 'blank': 'True'}),
            'not_deleted': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'primary': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.ManagedTarget']"})
        },
        'configure.mdtconfparam': {
            'Meta': {'object_name': 'MdtConfParam', '_ormbases': ['configure.ConfParam']},
            'confparam_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['configure.ConfParam']", 'unique': 'True', 'primary_key': 'True'}),
            'mdt': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.ManagedMdt']"})
        },
        'configure.monitor': {
            'Meta': {'object_name': 'Monitor'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'counter': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'host': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['configure.ManagedHost']", 'unique': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_success': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'default': "'idle'", 'max_length': '32'}),
            'task_id': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '36', 'null': 'True', 'blank': 'True'})
        },
        'configure.nid': {
            'Meta': {'object_name': 'Nid'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lnet_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.LNetConfiguration']"}),
            'nid_string': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        'configure.opportunisticjob': {
            'Meta': {'object_name': 'OpportunisticJob'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('picklefield.fields.PickledObjectField', [], {}),
            'run': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'run_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        'configure.ostconfparam': {
            'Meta': {'object_name': 'OstConfParam', '_ormbases': ['configure.ConfParam']},
            'confparam_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['configure.ConfParam']", 'unique': 'True', 'primary_key': 'True'}),
            'ost': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.ManagedOst']"})
        },
        'configure.registertargetjob': {
            'Meta': {'object_name': 'RegisterTargetJob', '_ormbases': ['configure.Job']},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['configure.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.ManagedTarget']"})
        },
        'configure.removefilesystemjob': {
            'Meta': {'object_name': 'RemoveFilesystemJob', '_ormbases': ['configure.Job']},
            'filesystem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.ManagedFilesystem']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['configure.Job']", 'unique': 'True', 'primary_key': 'True'})
        },
        'configure.removehostjob': {
            'Meta': {'object_name': 'RemoveHostJob', '_ormbases': ['configure.Job']},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.ManagedHost']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['configure.Job']", 'unique': 'True', 'primary_key': 'True'})
        },
        'configure.removeregisteredtargetjob': {
            'Meta': {'object_name': 'RemoveRegisteredTargetJob', '_ormbases': ['configure.Job']},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['configure.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.ManagedTarget']"})
        },
        'configure.removetargetjob_formatted': {
            'Meta': {'object_name': 'RemoveTargetJob_formatted', '_ormbases': ['configure.Job']},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['configure.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.ManagedTarget']"})
        },
        'configure.removetargetjob_unformatted': {
            'Meta': {'object_name': 'RemoveTargetJob_unformatted', '_ormbases': ['configure.Job']},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['configure.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.ManagedTarget']"})
        },
        'configure.removetargetmountjob': {
            'Meta': {'object_name': 'RemoveTargetMountJob', '_ormbases': ['configure.Job']},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['configure.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'target_mount': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.ManagedTargetMount']"})
        },
        'configure.removeunconfiguredtargetmountjob': {
            'Meta': {'object_name': 'RemoveUnconfiguredTargetMountJob', '_ormbases': ['configure.Job']},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['configure.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'target_mount': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.ManagedTargetMount']"})
        },
        'configure.setuphostjob': {
            'Meta': {'object_name': 'SetupHostJob', '_ormbases': ['configure.Job']},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['configure.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'managed_host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.ManagedHost']"})
        },
        'configure.simplehistostorebin': {
            'Meta': {'object_name': 'SimpleHistoStoreBin'},
            'bin_idx': ('django.db.models.fields.IntegerField', [], {}),
            'histo_store_time': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.SimpleHistoStoreTime']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'value': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        'configure.simplehistostoretime': {
            'Meta': {'object_name': 'SimpleHistoStoreTime'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'storage_resource_statistic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.StorageResourceStatistic']"}),
            'time': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        'configure.simplescalarstoredatapoint': {
            'Meta': {'object_name': 'SimpleScalarStoreDatapoint'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'storage_resource_statistic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.StorageResourceStatistic']"}),
            'time': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'value': ('django.db.models.fields.BigIntegerField', [], {})
        },
        'configure.startlnetjob': {
            'Meta': {'object_name': 'StartLNetJob', '_ormbases': ['configure.Job']},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.ManagedHost']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['configure.Job']", 'unique': 'True', 'primary_key': 'True'})
        },
        'configure.startstoppedfilesystemjob': {
            'Meta': {'object_name': 'StartStoppedFilesystemJob', '_ormbases': ['configure.Job']},
            'filesystem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.ManagedFilesystem']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['configure.Job']", 'unique': 'True', 'primary_key': 'True'})
        },
        'configure.starttargetjob': {
            'Meta': {'object_name': 'StartTargetJob', '_ormbases': ['configure.Job']},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['configure.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.ManagedTarget']"})
        },
        'configure.startunavailablefilesystemjob': {
            'Meta': {'object_name': 'StartUnavailableFilesystemJob', '_ormbases': ['configure.Job']},
            'filesystem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.ManagedFilesystem']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['configure.Job']", 'unique': 'True', 'primary_key': 'True'})
        },
        'configure.statelock': {
            'Meta': {'object_name': 'StateLock'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.Job']"}),
            'locked_item_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'locked_item_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'locked_item'", 'to': "orm['contenttypes.ContentType']"})
        },
        'configure.statereadlock': {
            'Meta': {'object_name': 'StateReadLock', '_ormbases': ['configure.StateLock']},
            'statelock_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['configure.StateLock']", 'unique': 'True', 'primary_key': 'True'})
        },
        'configure.statewritelock': {
            'Meta': {'object_name': 'StateWriteLock', '_ormbases': ['configure.StateLock']},
            'begin_state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'end_state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'statelock_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['configure.StateLock']", 'unique': 'True', 'primary_key': 'True'})
        },
        'configure.stepresult': {
            'Meta': {'object_name': 'StepResult'},
            'args': ('picklefield.fields.PickledObjectField', [], {}),
            'backtrace': ('django.db.models.fields.TextField', [], {}),
            'console': ('django.db.models.fields.TextField', [], {}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'exception': ('picklefield.fields.PickledObjectField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.Job']"}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'default': "'incomplete'", 'max_length': '32'}),
            'step_count': ('django.db.models.fields.IntegerField', [], {}),
            'step_index': ('django.db.models.fields.IntegerField', [], {}),
            'step_klass': ('picklefield.fields.PickledObjectField', [], {})
        },
        'configure.stoplnetjob': {
            'Meta': {'object_name': 'StopLNetJob', '_ormbases': ['configure.Job']},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.ManagedHost']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['configure.Job']", 'unique': 'True', 'primary_key': 'True'})
        },
        'configure.stoptargetjob': {
            'Meta': {'object_name': 'StopTargetJob', '_ormbases': ['configure.Job']},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['configure.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.ManagedTarget']"})
        },
        'configure.stopunavailablefilesystemjob': {
            'Meta': {'object_name': 'StopUnavailableFilesystemJob', '_ormbases': ['configure.Job']},
            'filesystem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.ManagedFilesystem']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['configure.Job']", 'unique': 'True', 'primary_key': 'True'})
        },
        'configure.storagealertpropagated': {
            'Meta': {'unique_together': "(('storage_resource', 'alert_state'),)", 'object_name': 'StorageAlertPropagated'},
            'alert_state': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.StorageResourceAlert']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'storage_resource': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.StorageResourceRecord']"})
        },
        'configure.storagepluginrecord': {
            'Meta': {'unique_together': "(('module_name',),)", 'object_name': 'StoragePluginRecord'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'module_name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        'configure.storageresourcealert': {
            'Meta': {'object_name': 'StorageResourceAlert', '_ormbases': ['monitor.AlertState']},
            'alert_class': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'alertstate_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['monitor.AlertState']", 'unique': 'True', 'primary_key': 'True'}),
            'attribute': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'})
        },
        'configure.storageresourceattribute': {
            'Meta': {'unique_together': "(('resource', 'key'),)", 'object_name': 'StorageResourceAttribute'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'resource': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.StorageResourceRecord']"}),
            'value': ('django.db.models.fields.TextField', [], {})
        },
        'configure.storageresourceclass': {
            'Meta': {'unique_together': "(('storage_plugin', 'class_name'),)", 'object_name': 'StorageResourceClass'},
            'class_name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'storage_plugin': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.StoragePluginRecord']"})
        },
        'configure.storageresourceclassstatistic': {
            'Meta': {'unique_together': "(('resource_class', 'name'),)", 'object_name': 'StorageResourceClassStatistic'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'resource_class': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.StorageResourceClass']"})
        },
        'configure.storageresourcelearnevent': {
            'Meta': {'object_name': 'StorageResourceLearnEvent', '_ormbases': ['monitor.Event']},
            'event_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['monitor.Event']", 'unique': 'True', 'primary_key': 'True'}),
            'storage_resource': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.StorageResourceRecord']"})
        },
        'configure.storageresourcerecord': {
            'Meta': {'unique_together': "(('storage_id_str', 'storage_id_scope', 'resource_class'),)", 'object_name': 'StorageResourceRecord'},
            'alias': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'parents': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'resource_parent'", 'symmetrical': 'False', 'to': "orm['configure.StorageResourceRecord']"}),
            'resource_class': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.StorageResourceClass']"}),
            'storage_id_scope': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.StorageResourceRecord']", 'null': 'True', 'blank': 'True'}),
            'storage_id_str': ('django.db.models.fields.CharField', [], {'max_length': '256'})
        },
        'configure.storageresourcestatistic': {
            'Meta': {'unique_together': "(('storage_resource', 'name'),)", 'object_name': 'StorageResourceStatistic'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'sample_period': ('django.db.models.fields.IntegerField', [], {}),
            'storage_resource': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.StorageResourceRecord']"})
        },
        'configure.unloadlnetjob': {
            'Meta': {'object_name': 'UnloadLNetJob', '_ormbases': ['configure.Job']},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.ManagedHost']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['configure.Job']", 'unique': 'True', 'primary_key': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'monitor.alertstate': {
            'Meta': {'unique_together': "(('alert_item_type', 'alert_item_id', 'content_type', 'active'),)", 'object_name': 'AlertState'},
            'active': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'alert_item_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'alert_item_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'alertstate_alert_item_type'", 'to': "orm['contenttypes.ContentType']"}),
            'begin': ('django.db.models.fields.DateTimeField', [], {}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'end': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'monitor.event': {
            'Meta': {'object_name': 'Event'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.ManagedHost']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'severity': ('django.db.models.fields.IntegerField', [], {})
        }
    }

    complete_apps = ['configure']
