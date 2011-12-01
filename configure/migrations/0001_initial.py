# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'StateLock'
        db.create_table('configure_statelock', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('job', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.Job'])),
            ('locked_item_type', self.gf('django.db.models.fields.related.ForeignKey')(related_name='locked_item', to=orm['contenttypes.ContentType'])),
            ('locked_item_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'], null=True)),
        ))
        db.send_create_signal('configure', ['StateLock'])

        # Adding model 'StateReadLock'
        db.create_table('configure_statereadlock', (
            ('statelock_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['configure.StateLock'], unique=True, primary_key=True)),
        ))
        db.send_create_signal('configure', ['StateReadLock'])

        # Adding model 'StateWriteLock'
        db.create_table('configure_statewritelock', (
            ('statelock_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['configure.StateLock'], unique=True, primary_key=True)),
            ('begin_state', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('end_state', self.gf('django.db.models.fields.CharField')(max_length=32)),
        ))
        db.send_create_signal('configure', ['StateWriteLock'])

        # Adding model 'Job'
        db.create_table('configure_job', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('state', self.gf('django.db.models.fields.CharField')(default='pending', max_length=16)),
            ('errored', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('paused', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('cancelled', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('modified_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('wait_for_count', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('wait_for_completions', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('task_id', self.gf('django.db.models.fields.CharField')(max_length=36, null=True, blank=True)),
            ('started_step', self.gf('django.db.models.fields.PositiveIntegerField')(default=None, null=True, blank=True)),
            ('finished_step', self.gf('django.db.models.fields.PositiveIntegerField')(default=None, null=True, blank=True)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'], null=True)),
        ))
        db.send_create_signal('configure', ['Job'])

        # Adding M2M table for field wait_for on 'Job'
        db.create_table('configure_job_wait_for', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('from_job', models.ForeignKey(orm['configure.job'], null=False)),
            ('to_job', models.ForeignKey(orm['configure.job'], null=False))
        ))
        db.create_unique('configure_job_wait_for', ['from_job_id', 'to_job_id'])

        # Adding model 'StepResult'
        db.create_table('configure_stepresult', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('job', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.Job'])),
            ('step_klass', self.gf('picklefield.fields.PickledObjectField')()),
            ('args', self.gf('picklefield.fields.PickledObjectField')()),
            ('step_index', self.gf('django.db.models.fields.IntegerField')()),
            ('step_count', self.gf('django.db.models.fields.IntegerField')()),
            ('console', self.gf('django.db.models.fields.TextField')()),
            ('exception', self.gf('picklefield.fields.PickledObjectField')(default=None, null=True, blank=True)),
            ('backtrace', self.gf('django.db.models.fields.TextField')()),
            ('state', self.gf('django.db.models.fields.CharField')(default='incomplete', max_length=32)),
            ('modified_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('configure', ['StepResult'])

        # Adding model 'ManagedHost'
        db.create_table('configure_managedhost', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('state', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('not_deleted', self.gf('django.db.models.fields.NullBooleanField')(default=True, null=True, blank=True)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'], null=True)),
            ('address', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
            ('fqdn', self.gf('django.db.models.fields.CharField')(max_length=255, unique=True, null=True, blank=True)),
        ))
        db.send_create_signal('configure', ['ManagedHost'])

        # Adding unique constraint on 'ManagedHost', fields ['address', 'not_deleted']
        db.create_unique('configure_managedhost', ['address', 'not_deleted'])

        # Adding model 'Lun'
        db.create_table('configure_lun', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('storage_resource', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.StorageResourceRecord'], null=True, blank=True)),
            ('size', self.gf('django.db.models.fields.BigIntegerField')(null=True, blank=True)),
            ('shareable', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('configure', ['Lun'])

        # Adding unique constraint on 'Lun', fields ['storage_resource']
        db.create_unique('configure_lun', ['storage_resource_id'])

        # Adding model 'LunNode'
        db.create_table('configure_lunnode', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('lun', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.Lun'])),
            ('host', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.ManagedHost'])),
            ('path', self.gf('django.db.models.fields.CharField')(max_length=512)),
            ('storage_resource', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.StorageResourceRecord'], null=True, blank=True)),
            ('primary', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('use', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal('configure', ['LunNode'])

        # Adding unique constraint on 'LunNode', fields ['host', 'path']
        db.create_unique('configure_lunnode', ['host_id', 'path'])

        # Adding model 'Monitor'
        db.create_table('configure_monitor', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('host', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['configure.ManagedHost'], unique=True)),
            ('state', self.gf('django.db.models.fields.CharField')(default='idle', max_length=32)),
            ('task_id', self.gf('django.db.models.fields.CharField')(default=None, max_length=36, null=True, blank=True)),
            ('counter', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('last_success', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'], null=True)),
        ))
        db.send_create_signal('configure', ['Monitor'])

        # Adding model 'LNetConfiguration'
        db.create_table('configure_lnetconfiguration', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('state', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('host', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['configure.ManagedHost'], unique=True)),
        ))
        db.send_create_signal('configure', ['LNetConfiguration'])

        # Adding model 'Nid'
        db.create_table('configure_nid', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('lnet_configuration', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.LNetConfiguration'])),
            ('nid_string', self.gf('django.db.models.fields.CharField')(max_length=128)),
        ))
        db.send_create_signal('configure', ['Nid'])

        # Adding model 'ConfigureLNetJob'
        db.create_table('configure_configurelnetjob', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['configure.Job'], unique=True, primary_key=True)),
            ('lnet_configuration', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.LNetConfiguration'])),
        ))
        db.send_create_signal('configure', ['ConfigureLNetJob'])

        # Adding model 'SetupHostJob'
        db.create_table('configure_setuphostjob', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['configure.Job'], unique=True, primary_key=True)),
            ('managed_host', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.ManagedHost'])),
        ))
        db.send_create_signal('configure', ['SetupHostJob'])

        # Adding model 'DetectTargetsJob'
        db.create_table('configure_detecttargetsjob', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['configure.Job'], unique=True, primary_key=True)),
        ))
        db.send_create_signal('configure', ['DetectTargetsJob'])

        # Adding model 'LoadLNetJob'
        db.create_table('configure_loadlnetjob', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['configure.Job'], unique=True, primary_key=True)),
            ('host', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.ManagedHost'])),
        ))
        db.send_create_signal('configure', ['LoadLNetJob'])

        # Adding model 'UnloadLNetJob'
        db.create_table('configure_unloadlnetjob', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['configure.Job'], unique=True, primary_key=True)),
            ('host', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.ManagedHost'])),
        ))
        db.send_create_signal('configure', ['UnloadLNetJob'])

        # Adding model 'StartLNetJob'
        db.create_table('configure_startlnetjob', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['configure.Job'], unique=True, primary_key=True)),
            ('host', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.ManagedHost'])),
        ))
        db.send_create_signal('configure', ['StartLNetJob'])

        # Adding model 'StopLNetJob'
        db.create_table('configure_stoplnetjob', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['configure.Job'], unique=True, primary_key=True)),
            ('host', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.ManagedHost'])),
        ))
        db.send_create_signal('configure', ['StopLNetJob'])

        # Adding model 'RemoveHostJob'
        db.create_table('configure_removehostjob', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['configure.Job'], unique=True, primary_key=True)),
            ('host', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.ManagedHost'])),
        ))
        db.send_create_signal('configure', ['RemoveHostJob'])

        # Adding model 'ManagedTarget'
        db.create_table('configure_managedtarget', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('state', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
            ('uuid', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
            ('active_mount', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.ManagedTargetMount'], null=True, blank=True)),
            ('not_deleted', self.gf('django.db.models.fields.NullBooleanField')(default=True, null=True, blank=True)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'], null=True)),
        ))
        db.send_create_signal('configure', ['ManagedTarget'])

        # Adding model 'ManagedOst'
        db.create_table('configure_managedost', (
            ('managedtarget_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['configure.ManagedTarget'], unique=True, primary_key=True)),
            ('filesystem', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.ManagedFilesystem'])),
        ))
        db.send_create_signal('configure', ['ManagedOst'])

        # Adding model 'ManagedMdt'
        db.create_table('configure_managedmdt', (
            ('managedtarget_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['configure.ManagedTarget'], unique=True, primary_key=True)),
            ('filesystem', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.ManagedFilesystem'])),
        ))
        db.send_create_signal('configure', ['ManagedMdt'])

        # Adding model 'ManagedMgs'
        db.create_table('configure_managedmgs', (
            ('managedtarget_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['configure.ManagedTarget'], unique=True, primary_key=True)),
            ('conf_param_version', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('conf_param_version_applied', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal('configure', ['ManagedMgs'])

        # Adding model 'RemoveRegisteredTargetJob'
        db.create_table('configure_removeregisteredtargetjob', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['configure.Job'], unique=True, primary_key=True)),
            ('target', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.ManagedTarget'])),
        ))
        db.send_create_signal('configure', ['RemoveRegisteredTargetJob'])

        # Adding model 'RemoveTargetJob_unformatted'
        db.create_table('configure_removetargetjob_unformatted', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['configure.Job'], unique=True, primary_key=True)),
            ('target', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.ManagedTarget'])),
        ))
        db.send_create_signal('configure', ['RemoveTargetJob_unformatted'])

        # Adding model 'RemoveTargetJob_formatted'
        db.create_table('configure_removetargetjob_formatted', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['configure.Job'], unique=True, primary_key=True)),
            ('target', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.ManagedTarget'])),
        ))
        db.send_create_signal('configure', ['RemoveTargetJob_formatted'])

        # Adding model 'RegisterTargetJob'
        db.create_table('configure_registertargetjob', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['configure.Job'], unique=True, primary_key=True)),
            ('target', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.ManagedTarget'])),
        ))
        db.send_create_signal('configure', ['RegisterTargetJob'])

        # Adding model 'StartTargetJob'
        db.create_table('configure_starttargetjob', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['configure.Job'], unique=True, primary_key=True)),
            ('target', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.ManagedTarget'])),
        ))
        db.send_create_signal('configure', ['StartTargetJob'])

        # Adding model 'StopTargetJob'
        db.create_table('configure_stoptargetjob', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['configure.Job'], unique=True, primary_key=True)),
            ('target', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.ManagedTarget'])),
        ))
        db.send_create_signal('configure', ['StopTargetJob'])

        # Adding model 'FormatTargetJob'
        db.create_table('configure_formattargetjob', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['configure.Job'], unique=True, primary_key=True)),
            ('target', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.ManagedTarget'])),
        ))
        db.send_create_signal('configure', ['FormatTargetJob'])

        # Adding model 'ManagedTargetMount'
        db.create_table('configure_managedtargetmount', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('state', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('not_deleted', self.gf('django.db.models.fields.NullBooleanField')(default=True, null=True, blank=True)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'], null=True)),
            ('host', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.ManagedHost'])),
            ('mount_point', self.gf('django.db.models.fields.CharField')(max_length=512, null=True, blank=True)),
            ('block_device', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.LunNode'])),
            ('primary', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('target', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.ManagedTarget'])),
        ))
        db.send_create_signal('configure', ['ManagedTargetMount'])

        # Adding model 'RemoveTargetMountJob'
        db.create_table('configure_removetargetmountjob', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['configure.Job'], unique=True, primary_key=True)),
            ('target_mount', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.ManagedTargetMount'])),
        ))
        db.send_create_signal('configure', ['RemoveTargetMountJob'])

        # Adding model 'RemoveUnconfiguredTargetMountJob'
        db.create_table('configure_removeunconfiguredtargetmountjob', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['configure.Job'], unique=True, primary_key=True)),
            ('target_mount', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.ManagedTargetMount'])),
        ))
        db.send_create_signal('configure', ['RemoveUnconfiguredTargetMountJob'])

        # Adding model 'ConfigureTargetMountJob'
        db.create_table('configure_configuretargetmountjob', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['configure.Job'], unique=True, primary_key=True)),
            ('target_mount', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.ManagedTargetMount'])),
        ))
        db.send_create_signal('configure', ['ConfigureTargetMountJob'])

        # Adding model 'ManagedFilesystem'
        db.create_table('configure_managedfilesystem', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('state', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=8)),
            ('mgs', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.ManagedMgs'])),
            ('not_deleted', self.gf('django.db.models.fields.NullBooleanField')(default=True, null=True, blank=True)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'], null=True)),
        ))
        db.send_create_signal('configure', ['ManagedFilesystem'])

        # Adding model 'RemoveFilesystemJob'
        db.create_table('configure_removefilesystemjob', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['configure.Job'], unique=True, primary_key=True)),
            ('filesystem', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.ManagedFilesystem'])),
        ))
        db.send_create_signal('configure', ['RemoveFilesystemJob'])

        # Adding model 'ApplyConfParams'
        db.create_table('configure_applyconfparams', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['configure.Job'], unique=True, primary_key=True)),
            ('mgs', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.ManagedMgs'])),
        ))
        db.send_create_signal('configure', ['ApplyConfParams'])

        # Adding model 'ConfParam'
        db.create_table('configure_confparam', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('mgs', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.ManagedMgs'])),
            ('key', self.gf('django.db.models.fields.CharField')(max_length=512)),
            ('value', self.gf('django.db.models.fields.CharField')(max_length=512, null=True, blank=True)),
            ('version', self.gf('django.db.models.fields.IntegerField')()),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'], null=True)),
        ))
        db.send_create_signal('configure', ['ConfParam'])

        # Adding model 'FilesystemClientConfParam'
        db.create_table('configure_filesystemclientconfparam', (
            ('confparam_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['configure.ConfParam'], unique=True, primary_key=True)),
            ('filesystem', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.ManagedFilesystem'])),
        ))
        db.send_create_signal('configure', ['FilesystemClientConfParam'])

        # Adding model 'FilesystemGlobalConfParam'
        db.create_table('configure_filesystemglobalconfparam', (
            ('confparam_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['configure.ConfParam'], unique=True, primary_key=True)),
            ('filesystem', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.ManagedFilesystem'])),
        ))
        db.send_create_signal('configure', ['FilesystemGlobalConfParam'])

        # Adding model 'MdtConfParam'
        db.create_table('configure_mdtconfparam', (
            ('confparam_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['configure.ConfParam'], unique=True, primary_key=True)),
            ('mdt', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.ManagedMdt'])),
        ))
        db.send_create_signal('configure', ['MdtConfParam'])

        # Adding model 'OstConfParam'
        db.create_table('configure_ostconfparam', (
            ('confparam_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['configure.ConfParam'], unique=True, primary_key=True)),
            ('ost', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.ManagedOst'])),
        ))
        db.send_create_signal('configure', ['OstConfParam'])

        # Adding model 'StoragePluginRecord'
        db.create_table('configure_storagepluginrecord', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('module_name', self.gf('django.db.models.fields.CharField')(max_length=128)),
        ))
        db.send_create_signal('configure', ['StoragePluginRecord'])

        # Adding unique constraint on 'StoragePluginRecord', fields ['module_name']
        db.create_unique('configure_storagepluginrecord', ['module_name'])

        # Adding model 'StorageResourceClass'
        db.create_table('configure_storageresourceclass', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('storage_plugin', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.StoragePluginRecord'])),
            ('class_name', self.gf('django.db.models.fields.CharField')(max_length=128)),
        ))
        db.send_create_signal('configure', ['StorageResourceClass'])

        # Adding unique constraint on 'StorageResourceClass', fields ['storage_plugin', 'class_name']
        db.create_unique('configure_storageresourceclass', ['storage_plugin_id', 'class_name'])

        # Adding model 'StorageResourceRecord'
        db.create_table('configure_storageresourcerecord', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('resource_class', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.StorageResourceClass'])),
            ('storage_id_str', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('storage_id_scope', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.StorageResourceRecord'], null=True, blank=True)),
            ('alias', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
        ))
        db.send_create_signal('configure', ['StorageResourceRecord'])

        # Adding unique constraint on 'StorageResourceRecord', fields ['storage_id_str', 'storage_id_scope', 'resource_class']
        db.create_unique('configure_storageresourcerecord', ['storage_id_str', 'storage_id_scope_id', 'resource_class_id'])

        # Adding M2M table for field parents on 'StorageResourceRecord'
        db.create_table('configure_storageresourcerecord_parents', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('from_storageresourcerecord', models.ForeignKey(orm['configure.storageresourcerecord'], null=False)),
            ('to_storageresourcerecord', models.ForeignKey(orm['configure.storageresourcerecord'], null=False))
        ))
        db.create_unique('configure_storageresourcerecord_parents', ['from_storageresourcerecord_id', 'to_storageresourcerecord_id'])

        # Adding model 'SimpleHistoStoreBin'
        db.create_table('configure_simplehistostorebin', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('histo_store_time', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.SimpleHistoStoreTime'])),
            ('bin_idx', self.gf('django.db.models.fields.IntegerField')()),
            ('value', self.gf('django.db.models.fields.PositiveIntegerField')()),
        ))
        db.send_create_signal('configure', ['SimpleHistoStoreBin'])

        # Adding model 'SimpleHistoStoreTime'
        db.create_table('configure_simplehistostoretime', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('storage_resource_statistic', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.StorageResourceStatistic'])),
            ('time', self.gf('django.db.models.fields.PositiveIntegerField')()),
        ))
        db.send_create_signal('configure', ['SimpleHistoStoreTime'])

        # Adding model 'SimpleScalarStoreDatapoint'
        db.create_table('configure_simplescalarstoredatapoint', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('storage_resource_statistic', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.StorageResourceStatistic'])),
            ('time', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('value', self.gf('django.db.models.fields.BigIntegerField')()),
        ))
        db.send_create_signal('configure', ['SimpleScalarStoreDatapoint'])

        # Adding model 'StorageResourceStatistic'
        db.create_table('configure_storageresourcestatistic', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('storage_resource', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.StorageResourceRecord'])),
            ('sample_period', self.gf('django.db.models.fields.IntegerField')()),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=64)),
        ))
        db.send_create_signal('configure', ['StorageResourceStatistic'])

        # Adding unique constraint on 'StorageResourceStatistic', fields ['storage_resource', 'name']
        db.create_unique('configure_storageresourcestatistic', ['storage_resource_id', 'name'])

        # Adding model 'StorageResourceAttribute'
        db.create_table('configure_storageresourceattribute', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('resource', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.StorageResourceRecord'])),
            ('value', self.gf('django.db.models.fields.TextField')()),
            ('key', self.gf('django.db.models.fields.CharField')(max_length=64)),
        ))
        db.send_create_signal('configure', ['StorageResourceAttribute'])

        # Adding unique constraint on 'StorageResourceAttribute', fields ['resource', 'key']
        db.create_unique('configure_storageresourceattribute', ['resource_id', 'key'])

        # Adding model 'StorageResourceClassStatistic'
        db.create_table('configure_storageresourceclassstatistic', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('resource_class', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.StorageResourceClass'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=64)),
        ))
        db.send_create_signal('configure', ['StorageResourceClassStatistic'])

        # Adding unique constraint on 'StorageResourceClassStatistic', fields ['resource_class', 'name']
        db.create_unique('configure_storageresourceclassstatistic', ['resource_class_id', 'name'])

        # Adding model 'StorageResourceAlert'
        db.create_table('configure_storageresourcealert', (
            ('alertstate_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['monitor.AlertState'], unique=True, primary_key=True)),
            ('alert_class', self.gf('django.db.models.fields.CharField')(max_length=512)),
            ('attribute', self.gf('django.db.models.fields.CharField')(max_length=128, null=True, blank=True)),
        ))
        db.send_create_signal('configure', ['StorageResourceAlert'])

        # Adding model 'StorageAlertPropagated'
        db.create_table('configure_storagealertpropagated', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('storage_resource', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.StorageResourceRecord'])),
            ('alert_state', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.StorageResourceAlert'])),
        ))
        db.send_create_signal('configure', ['StorageAlertPropagated'])

        # Adding unique constraint on 'StorageAlertPropagated', fields ['storage_resource', 'alert_state']
        db.create_unique('configure_storagealertpropagated', ['storage_resource_id', 'alert_state_id'])

        # Adding model 'StorageResourceLearnEvent'
        db.create_table('configure_storageresourcelearnevent', (
            ('event_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['monitor.Event'], unique=True, primary_key=True)),
            ('storage_resource', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['configure.StorageResourceRecord'])),
        ))
        db.send_create_signal('configure', ['StorageResourceLearnEvent'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'StorageAlertPropagated', fields ['storage_resource', 'alert_state']
        db.delete_unique('configure_storagealertpropagated', ['storage_resource_id', 'alert_state_id'])

        # Removing unique constraint on 'StorageResourceClassStatistic', fields ['resource_class', 'name']
        db.delete_unique('configure_storageresourceclassstatistic', ['resource_class_id', 'name'])

        # Removing unique constraint on 'StorageResourceAttribute', fields ['resource', 'key']
        db.delete_unique('configure_storageresourceattribute', ['resource_id', 'key'])

        # Removing unique constraint on 'StorageResourceStatistic', fields ['storage_resource', 'name']
        db.delete_unique('configure_storageresourcestatistic', ['storage_resource_id', 'name'])

        # Removing unique constraint on 'StorageResourceRecord', fields ['storage_id_str', 'storage_id_scope', 'resource_class']
        db.delete_unique('configure_storageresourcerecord', ['storage_id_str', 'storage_id_scope_id', 'resource_class_id'])

        # Removing unique constraint on 'StorageResourceClass', fields ['storage_plugin', 'class_name']
        db.delete_unique('configure_storageresourceclass', ['storage_plugin_id', 'class_name'])

        # Removing unique constraint on 'StoragePluginRecord', fields ['module_name']
        db.delete_unique('configure_storagepluginrecord', ['module_name'])

        # Removing unique constraint on 'LunNode', fields ['host', 'path']
        db.delete_unique('configure_lunnode', ['host_id', 'path'])

        # Removing unique constraint on 'Lun', fields ['storage_resource']
        db.delete_unique('configure_lun', ['storage_resource_id'])

        # Removing unique constraint on 'ManagedHost', fields ['address', 'not_deleted']
        db.delete_unique('configure_managedhost', ['address', 'not_deleted'])

        # Deleting model 'StateLock'
        db.delete_table('configure_statelock')

        # Deleting model 'StateReadLock'
        db.delete_table('configure_statereadlock')

        # Deleting model 'StateWriteLock'
        db.delete_table('configure_statewritelock')

        # Deleting model 'Job'
        db.delete_table('configure_job')

        # Removing M2M table for field wait_for on 'Job'
        db.delete_table('configure_job_wait_for')

        # Deleting model 'StepResult'
        db.delete_table('configure_stepresult')

        # Deleting model 'ManagedHost'
        db.delete_table('configure_managedhost')

        # Deleting model 'Lun'
        db.delete_table('configure_lun')

        # Deleting model 'LunNode'
        db.delete_table('configure_lunnode')

        # Deleting model 'Monitor'
        db.delete_table('configure_monitor')

        # Deleting model 'LNetConfiguration'
        db.delete_table('configure_lnetconfiguration')

        # Deleting model 'Nid'
        db.delete_table('configure_nid')

        # Deleting model 'ConfigureLNetJob'
        db.delete_table('configure_configurelnetjob')

        # Deleting model 'SetupHostJob'
        db.delete_table('configure_setuphostjob')

        # Deleting model 'DetectTargetsJob'
        db.delete_table('configure_detecttargetsjob')

        # Deleting model 'LoadLNetJob'
        db.delete_table('configure_loadlnetjob')

        # Deleting model 'UnloadLNetJob'
        db.delete_table('configure_unloadlnetjob')

        # Deleting model 'StartLNetJob'
        db.delete_table('configure_startlnetjob')

        # Deleting model 'StopLNetJob'
        db.delete_table('configure_stoplnetjob')

        # Deleting model 'RemoveHostJob'
        db.delete_table('configure_removehostjob')

        # Deleting model 'ManagedTarget'
        db.delete_table('configure_managedtarget')

        # Deleting model 'ManagedOst'
        db.delete_table('configure_managedost')

        # Deleting model 'ManagedMdt'
        db.delete_table('configure_managedmdt')

        # Deleting model 'ManagedMgs'
        db.delete_table('configure_managedmgs')

        # Deleting model 'RemoveRegisteredTargetJob'
        db.delete_table('configure_removeregisteredtargetjob')

        # Deleting model 'RemoveTargetJob_unformatted'
        db.delete_table('configure_removetargetjob_unformatted')

        # Deleting model 'RemoveTargetJob_formatted'
        db.delete_table('configure_removetargetjob_formatted')

        # Deleting model 'RegisterTargetJob'
        db.delete_table('configure_registertargetjob')

        # Deleting model 'StartTargetJob'
        db.delete_table('configure_starttargetjob')

        # Deleting model 'StopTargetJob'
        db.delete_table('configure_stoptargetjob')

        # Deleting model 'FormatTargetJob'
        db.delete_table('configure_formattargetjob')

        # Deleting model 'ManagedTargetMount'
        db.delete_table('configure_managedtargetmount')

        # Deleting model 'RemoveTargetMountJob'
        db.delete_table('configure_removetargetmountjob')

        # Deleting model 'RemoveUnconfiguredTargetMountJob'
        db.delete_table('configure_removeunconfiguredtargetmountjob')

        # Deleting model 'ConfigureTargetMountJob'
        db.delete_table('configure_configuretargetmountjob')

        # Deleting model 'ManagedFilesystem'
        db.delete_table('configure_managedfilesystem')

        # Deleting model 'RemoveFilesystemJob'
        db.delete_table('configure_removefilesystemjob')

        # Deleting model 'ApplyConfParams'
        db.delete_table('configure_applyconfparams')

        # Deleting model 'ConfParam'
        db.delete_table('configure_confparam')

        # Deleting model 'FilesystemClientConfParam'
        db.delete_table('configure_filesystemclientconfparam')

        # Deleting model 'FilesystemGlobalConfParam'
        db.delete_table('configure_filesystemglobalconfparam')

        # Deleting model 'MdtConfParam'
        db.delete_table('configure_mdtconfparam')

        # Deleting model 'OstConfParam'
        db.delete_table('configure_ostconfparam')

        # Deleting model 'StoragePluginRecord'
        db.delete_table('configure_storagepluginrecord')

        # Deleting model 'StorageResourceClass'
        db.delete_table('configure_storageresourceclass')

        # Deleting model 'StorageResourceRecord'
        db.delete_table('configure_storageresourcerecord')

        # Removing M2M table for field parents on 'StorageResourceRecord'
        db.delete_table('configure_storageresourcerecord_parents')

        # Deleting model 'SimpleHistoStoreBin'
        db.delete_table('configure_simplehistostorebin')

        # Deleting model 'SimpleHistoStoreTime'
        db.delete_table('configure_simplehistostoretime')

        # Deleting model 'SimpleScalarStoreDatapoint'
        db.delete_table('configure_simplescalarstoredatapoint')

        # Deleting model 'StorageResourceStatistic'
        db.delete_table('configure_storageresourcestatistic')

        # Deleting model 'StorageResourceAttribute'
        db.delete_table('configure_storageresourceattribute')

        # Deleting model 'StorageResourceClassStatistic'
        db.delete_table('configure_storageresourceclassstatistic')

        # Deleting model 'StorageResourceAlert'
        db.delete_table('configure_storageresourcealert')

        # Deleting model 'StorageAlertPropagated'
        db.delete_table('configure_storagealertpropagated')

        # Deleting model 'StorageResourceLearnEvent'
        db.delete_table('configure_storageresourcelearnevent')


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
            'Meta': {'unique_together': "(('host', 'path'),)", 'object_name': 'LunNode'},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.ManagedHost']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lun': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.Lun']"}),
            'path': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'primary': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'storage_resource': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.StorageResourceRecord']", 'null': 'True', 'blank': 'True'}),
            'use': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
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
            'address': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'fqdn': ('django.db.models.fields.CharField', [], {'max_length': '255', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
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
        'configure.starttargetjob': {
            'Meta': {'object_name': 'StartTargetJob', '_ormbases': ['configure.Job']},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['configure.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.ManagedTarget']"})
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
