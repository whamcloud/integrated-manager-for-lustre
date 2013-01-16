# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Command'
        db.create_table('chroma_core_command', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('complete', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('errored', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('cancelled', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('message', self.gf('django.db.models.fields.CharField')(max_length=512)),
            ('created_at', self.gf('chroma_core.models.utils.WorkaroundDateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('chroma_core', ['Command'])

        # Adding M2M table for field jobs on 'Command'
        db.create_table('chroma_core_command_jobs', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('command', models.ForeignKey(orm['chroma_core.command'], null=False)),
            ('job', models.ForeignKey(orm['chroma_core.job'], null=False))
        ))
        db.create_unique('chroma_core_command_jobs', ['command_id', 'job_id'])

        # Adding model 'Job'
        db.create_table('chroma_core_job', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('state', self.gf('django.db.models.fields.CharField')(default='pending', max_length=16)),
            ('errored', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('paused', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('cancelled', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('modified_at', self.gf('chroma_core.models.utils.WorkaroundDateTimeField')(auto_now=True, blank=True)),
            ('created_at', self.gf('chroma_core.models.utils.WorkaroundDateTimeField')(auto_now_add=True, blank=True)),
            ('wait_for_json', self.gf('django.db.models.fields.TextField')()),
            ('task_id', self.gf('django.db.models.fields.CharField')(max_length=36, null=True, blank=True)),
            ('locks_json', self.gf('django.db.models.fields.TextField')()),
            ('started_step', self.gf('django.db.models.fields.PositiveIntegerField')(default=None, null=True, blank=True)),
            ('finished_step', self.gf('django.db.models.fields.PositiveIntegerField')(default=None, null=True, blank=True)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'], null=True)),
        ))
        db.send_create_signal('chroma_core', ['Job'])

        # Adding model 'StepResult'
        db.create_table('chroma_core_stepresult', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('job', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.Job'])),
            ('step_klass', self.gf('picklefield.fields.PickledObjectField')()),
            ('args', self.gf('picklefield.fields.PickledObjectField')()),
            ('step_index', self.gf('django.db.models.fields.IntegerField')()),
            ('step_count', self.gf('django.db.models.fields.IntegerField')()),
            ('console', self.gf('django.db.models.fields.TextField')()),
            ('exception', self.gf('picklefield.fields.PickledObjectField')(default=None, null=True, blank=True)),
            ('backtrace', self.gf('django.db.models.fields.TextField')()),
            ('state', self.gf('django.db.models.fields.CharField')(default='incomplete', max_length=32)),
            ('modified_at', self.gf('chroma_core.models.utils.WorkaroundDateTimeField')(auto_now=True, blank=True)),
            ('created_at', self.gf('chroma_core.models.utils.WorkaroundDateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('chroma_core', ['StepResult'])

        # Adding model 'AlertState'
        db.create_table('chroma_core_alertstate', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('alert_item_type', self.gf('django.db.models.fields.related.ForeignKey')(related_name='alertstate_alert_item_type', to=orm['contenttypes.ContentType'])),
            ('alert_item_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('alert_type', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('begin', self.gf('chroma_core.models.utils.WorkaroundDateTimeField')()),
            ('end', self.gf('chroma_core.models.utils.WorkaroundDateTimeField')()),
            ('active', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
            ('dismissed', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'], null=True)),
        ))
        db.send_create_signal('chroma_core', ['AlertState'])

        # Adding unique constraint on 'AlertState', fields ['alert_item_type', 'alert_item_id', 'alert_type', 'active']
        db.create_unique('chroma_core_alertstate', ['alert_item_type_id', 'alert_item_id', 'alert_type', 'active'])

        # Adding model 'AlertSubscription'
        db.create_table('chroma_core_alertsubscription', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='alert_subscriptions', to=orm['auth.User'])),
            ('alert_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
        ))
        db.send_create_signal('chroma_core', ['AlertSubscription'])

        # Adding model 'AlertEmail'
        db.create_table('chroma_core_alertemail', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('chroma_core', ['AlertEmail'])

        # Adding M2M table for field alerts on 'AlertEmail'
        db.create_table('chroma_core_alertemail_alerts', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('alertemail', models.ForeignKey(orm['chroma_core.alertemail'], null=False)),
            ('alertstate', models.ForeignKey(orm['chroma_core.alertstate'], null=False))
        ))
        db.create_unique('chroma_core_alertemail_alerts', ['alertemail_id', 'alertstate_id'])

        # Adding model 'Event'
        db.create_table('chroma_core_event', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_at', self.gf('chroma_core.models.utils.WorkaroundDateTimeField')(auto_now_add=True, blank=True)),
            ('severity', self.gf('django.db.models.fields.IntegerField')()),
            ('host', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.ManagedHost'], null=True, blank=True)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'], null=True)),
        ))
        db.send_create_signal('chroma_core', ['Event'])

        # Adding model 'LearnEvent'
        db.create_table('chroma_core_learnevent', (
            ('event_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.Event'], unique=True, primary_key=True)),
            ('learned_item_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
            ('learned_item_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
        ))
        db.send_create_signal('chroma_core', ['LearnEvent'])

        # Adding model 'AlertEvent'
        db.create_table('chroma_core_alertevent', (
            ('event_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.Event'], unique=True, primary_key=True)),
            ('message_str', self.gf('django.db.models.fields.CharField')(max_length=512)),
            ('alert', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.AlertState'])),
        ))
        db.send_create_signal('chroma_core', ['AlertEvent'])

        # Adding model 'SyslogEvent'
        db.create_table('chroma_core_syslogevent', (
            ('event_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.Event'], unique=True, primary_key=True)),
            ('message_str', self.gf('django.db.models.fields.CharField')(max_length=512)),
            ('lustre_pid', self.gf('django.db.models.fields.IntegerField')(null=True)),
        ))
        db.send_create_signal('chroma_core', ['SyslogEvent'])

        # Adding model 'ClientConnectEvent'
        db.create_table('chroma_core_clientconnectevent', (
            ('event_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.Event'], unique=True, primary_key=True)),
            ('message_str', self.gf('django.db.models.fields.CharField')(max_length=512)),
            ('lustre_pid', self.gf('django.db.models.fields.IntegerField')(null=True)),
        ))
        db.send_create_signal('chroma_core', ['ClientConnectEvent'])

        # Adding model 'ManagedHost'
        db.create_table('chroma_core_managedhost', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('state_modified_at', self.gf('chroma_core.models.utils.WorkaroundDateTimeField')()),
            ('state', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('immutable_state', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('not_deleted', self.gf('django.db.models.fields.NullBooleanField')(default=True, null=True, blank=True)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'], null=True)),
            ('address', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('fqdn', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('nodename', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('agent_token', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('last_contact', self.gf('chroma_core.models.utils.WorkaroundDateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal('chroma_core', ['ManagedHost'])

        # Adding unique constraint on 'ManagedHost', fields ['address', 'not_deleted']
        db.create_unique('chroma_core_managedhost', ['address', 'not_deleted'])

        # Adding model 'Volume'
        db.create_table('chroma_core_volume', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('storage_resource', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.StorageResourceRecord'], null=True, blank=True)),
            ('size', self.gf('django.db.models.fields.BigIntegerField')(null=True, blank=True)),
            ('label', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('not_deleted', self.gf('django.db.models.fields.NullBooleanField')(default=True, null=True, blank=True)),
        ))
        db.send_create_signal('chroma_core', ['Volume'])

        # Adding unique constraint on 'Volume', fields ['storage_resource', 'not_deleted']
        db.create_unique('chroma_core_volume', ['storage_resource_id', 'not_deleted'])

        # Adding model 'VolumeNode'
        db.create_table('chroma_core_volumenode', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('volume', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.Volume'])),
            ('host', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.ManagedHost'])),
            ('path', self.gf('django.db.models.fields.CharField')(max_length=512)),
            ('storage_resource', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.StorageResourceRecord'], null=True, blank=True)),
            ('primary', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('use', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('not_deleted', self.gf('django.db.models.fields.NullBooleanField')(default=True, null=True, blank=True)),
        ))
        db.send_create_signal('chroma_core', ['VolumeNode'])

        # Adding unique constraint on 'VolumeNode', fields ['host', 'path', 'not_deleted']
        db.create_unique('chroma_core_volumenode', ['host_id', 'path', 'not_deleted'])

        # Adding model 'LNetConfiguration'
        db.create_table('chroma_core_lnetconfiguration', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('state_modified_at', self.gf('chroma_core.models.utils.WorkaroundDateTimeField')()),
            ('state', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('immutable_state', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('host', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.ManagedHost'], unique=True)),
        ))
        db.send_create_signal('chroma_core', ['LNetConfiguration'])

        # Adding model 'Nid'
        db.create_table('chroma_core_nid', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('lnet_configuration', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.LNetConfiguration'])),
            ('nid_string', self.gf('django.db.models.fields.CharField')(max_length=128)),
        ))
        db.send_create_signal('chroma_core', ['Nid'])

        # Adding model 'ConfigureLNetJob'
        db.create_table('chroma_core_configurelnetjob', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.Job'], unique=True, primary_key=True)),
            ('old_state', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('lnet_configuration', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.LNetConfiguration'])),
        ))
        db.send_create_signal('chroma_core', ['ConfigureLNetJob'])

        # Adding model 'GetLNetStateJob'
        db.create_table('chroma_core_getlnetstatejob', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.Job'], unique=True, primary_key=True)),
            ('host', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.ManagedHost'])),
        ))
        db.send_create_signal('chroma_core', ['GetLNetStateJob'])

        # Adding model 'SetupHostJob'
        db.create_table('chroma_core_setuphostjob', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.Job'], unique=True, primary_key=True)),
            ('old_state', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('managed_host', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.ManagedHost'])),
        ))
        db.send_create_signal('chroma_core', ['SetupHostJob'])

        # Adding model 'EnableLNetJob'
        db.create_table('chroma_core_enablelnetjob', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.Job'], unique=True, primary_key=True)),
            ('old_state', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('managed_host', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.ManagedHost'])),
        ))
        db.send_create_signal('chroma_core', ['EnableLNetJob'])

        # Adding model 'DetectTargetsJob'
        db.create_table('chroma_core_detecttargetsjob', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.Job'], unique=True, primary_key=True)),
        ))
        db.send_create_signal('chroma_core', ['DetectTargetsJob'])

        # Adding model 'LoadLNetJob'
        db.create_table('chroma_core_loadlnetjob', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.Job'], unique=True, primary_key=True)),
            ('old_state', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('host', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.ManagedHost'])),
        ))
        db.send_create_signal('chroma_core', ['LoadLNetJob'])

        # Adding model 'UnloadLNetJob'
        db.create_table('chroma_core_unloadlnetjob', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.Job'], unique=True, primary_key=True)),
            ('old_state', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('host', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.ManagedHost'])),
        ))
        db.send_create_signal('chroma_core', ['UnloadLNetJob'])

        # Adding model 'StartLNetJob'
        db.create_table('chroma_core_startlnetjob', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.Job'], unique=True, primary_key=True)),
            ('old_state', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('host', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.ManagedHost'])),
        ))
        db.send_create_signal('chroma_core', ['StartLNetJob'])

        # Adding model 'StopLNetJob'
        db.create_table('chroma_core_stoplnetjob', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.Job'], unique=True, primary_key=True)),
            ('old_state', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('host', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.ManagedHost'])),
        ))
        db.send_create_signal('chroma_core', ['StopLNetJob'])

        # Adding model 'RemoveHostJob'
        db.create_table('chroma_core_removehostjob', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.Job'], unique=True, primary_key=True)),
            ('old_state', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('host', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.ManagedHost'])),
        ))
        db.send_create_signal('chroma_core', ['RemoveHostJob'])

        # Adding model 'ForceRemoveHostJob'
        db.create_table('chroma_core_forceremovehostjob', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.Job'], unique=True, primary_key=True)),
            ('host', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.ManagedHost'])),
        ))
        db.send_create_signal('chroma_core', ['ForceRemoveHostJob'])

        # Adding model 'RemoveUnconfiguredHostJob'
        db.create_table('chroma_core_removeunconfiguredhostjob', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.Job'], unique=True, primary_key=True)),
            ('old_state', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('host', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.ManagedHost'])),
        ))
        db.send_create_signal('chroma_core', ['RemoveUnconfiguredHostJob'])

        # Adding model 'RelearnNidsJob'
        db.create_table('chroma_core_relearnnidsjob', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.Job'], unique=True, primary_key=True)),
            ('host', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.ManagedHost'])),
        ))
        db.send_create_signal('chroma_core', ['RelearnNidsJob'])

        # Adding model 'UpdateNidsJob'
        db.create_table('chroma_core_updatenidsjob', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.Job'], unique=True, primary_key=True)),
        ))
        db.send_create_signal('chroma_core', ['UpdateNidsJob'])

        # Adding model 'HostContactAlert'
        db.create_table('chroma_core_hostcontactalert', (
            ('alertstate_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.AlertState'], unique=True, primary_key=True)),
        ))
        db.send_create_signal('chroma_core', ['HostContactAlert'])

        # Adding model 'LNetOfflineAlert'
        db.create_table('chroma_core_lnetofflinealert', (
            ('alertstate_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.AlertState'], unique=True, primary_key=True)),
        ))
        db.send_create_signal('chroma_core', ['LNetOfflineAlert'])

        # Adding model 'LNetNidsChangedAlert'
        db.create_table('chroma_core_lnetnidschangedalert', (
            ('alertstate_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.AlertState'], unique=True, primary_key=True)),
        ))
        db.send_create_signal('chroma_core', ['LNetNidsChangedAlert'])

        # Adding model 'ManagedTarget'
        db.create_table('chroma_core_managedtarget', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('state_modified_at', self.gf('chroma_core.models.utils.WorkaroundDateTimeField')()),
            ('state', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('immutable_state', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
            ('uuid', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
            ('ha_label', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
            ('volume', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.Volume'])),
            ('inode_size', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('bytes_per_inode', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('inode_count', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('active_mount', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.ManagedTargetMount'], null=True, blank=True)),
            ('not_deleted', self.gf('django.db.models.fields.NullBooleanField')(default=True, null=True, blank=True)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'], null=True)),
        ))
        db.send_create_signal('chroma_core', ['ManagedTarget'])

        # Adding model 'ManagedOst'
        db.create_table('chroma_core_managedost', (
            ('managedtarget_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.ManagedTarget'], unique=True, primary_key=True)),
            ('filesystem', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.ManagedFilesystem'])),
        ))
        db.send_create_signal('chroma_core', ['ManagedOst'])

        # Adding model 'ManagedMdt'
        db.create_table('chroma_core_managedmdt', (
            ('managedtarget_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.ManagedTarget'], unique=True, primary_key=True)),
            ('filesystem', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.ManagedFilesystem'])),
        ))
        db.send_create_signal('chroma_core', ['ManagedMdt'])

        # Adding model 'ManagedMgs'
        db.create_table('chroma_core_managedmgs', (
            ('managedtarget_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.ManagedTarget'], unique=True, primary_key=True)),
            ('conf_param_version', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('conf_param_version_applied', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal('chroma_core', ['ManagedMgs'])

        # Adding model 'TargetRecoveryInfo'
        db.create_table('chroma_core_targetrecoveryinfo', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('recovery_status', self.gf('django.db.models.fields.TextField')()),
            ('target', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.ManagedTarget'])),
        ))
        db.send_create_signal('chroma_core', ['TargetRecoveryInfo'])

        # Adding model 'RemoveConfiguredTargetJob'
        db.create_table('chroma_core_removeconfiguredtargetjob', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.Job'], unique=True, primary_key=True)),
            ('old_state', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('target', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.ManagedTarget'])),
        ))
        db.send_create_signal('chroma_core', ['RemoveConfiguredTargetJob'])

        # Adding model 'RemoveTargetJob'
        db.create_table('chroma_core_removetargetjob', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.Job'], unique=True, primary_key=True)),
            ('old_state', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('target', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.ManagedTarget'])),
        ))
        db.send_create_signal('chroma_core', ['RemoveTargetJob'])

        # Adding model 'ForgetTargetJob'
        db.create_table('chroma_core_forgettargetjob', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.Job'], unique=True, primary_key=True)),
            ('old_state', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('target', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.ManagedTarget'])),
        ))
        db.send_create_signal('chroma_core', ['ForgetTargetJob'])

        # Adding model 'ConfigureTargetJob'
        db.create_table('chroma_core_configuretargetjob', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.Job'], unique=True, primary_key=True)),
            ('old_state', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('target', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.ManagedTarget'])),
        ))
        db.send_create_signal('chroma_core', ['ConfigureTargetJob'])

        # Adding model 'RegisterTargetJob'
        db.create_table('chroma_core_registertargetjob', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.Job'], unique=True, primary_key=True)),
            ('old_state', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('target', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.ManagedTarget'])),
        ))
        db.send_create_signal('chroma_core', ['RegisterTargetJob'])

        # Adding model 'StartTargetJob'
        db.create_table('chroma_core_starttargetjob', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.Job'], unique=True, primary_key=True)),
            ('old_state', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('target', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.ManagedTarget'])),
        ))
        db.send_create_signal('chroma_core', ['StartTargetJob'])

        # Adding model 'StopTargetJob'
        db.create_table('chroma_core_stoptargetjob', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.Job'], unique=True, primary_key=True)),
            ('old_state', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('target', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.ManagedTarget'])),
        ))
        db.send_create_signal('chroma_core', ['StopTargetJob'])

        # Adding model 'FormatTargetJob'
        db.create_table('chroma_core_formattargetjob', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.Job'], unique=True, primary_key=True)),
            ('old_state', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('target', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.ManagedTarget'])),
        ))
        db.send_create_signal('chroma_core', ['FormatTargetJob'])

        # Adding model 'ManagedTargetMount'
        db.create_table('chroma_core_managedtargetmount', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('host', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.ManagedHost'])),
            ('mount_point', self.gf('django.db.models.fields.CharField')(max_length=512, null=True, blank=True)),
            ('volume_node', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.VolumeNode'])),
            ('primary', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('target', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.ManagedTarget'])),
            ('not_deleted', self.gf('django.db.models.fields.NullBooleanField')(default=True, null=True, blank=True)),
        ))
        db.send_create_signal('chroma_core', ['ManagedTargetMount'])

        # Adding model 'TargetOfflineAlert'
        db.create_table('chroma_core_targetofflinealert', (
            ('alertstate_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.AlertState'], unique=True, primary_key=True)),
        ))
        db.send_create_signal('chroma_core', ['TargetOfflineAlert'])

        # Adding model 'TargetFailoverAlert'
        db.create_table('chroma_core_targetfailoveralert', (
            ('alertstate_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.AlertState'], unique=True, primary_key=True)),
        ))
        db.send_create_signal('chroma_core', ['TargetFailoverAlert'])

        # Adding model 'TargetRecoveryAlert'
        db.create_table('chroma_core_targetrecoveryalert', (
            ('alertstate_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.AlertState'], unique=True, primary_key=True)),
        ))
        db.send_create_signal('chroma_core', ['TargetRecoveryAlert'])

        # Adding model 'ManagedFilesystem'
        db.create_table('chroma_core_managedfilesystem', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('state_modified_at', self.gf('chroma_core.models.utils.WorkaroundDateTimeField')()),
            ('state', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('immutable_state', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=8)),
            ('mgs', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.ManagedMgs'])),
            ('not_deleted', self.gf('django.db.models.fields.NullBooleanField')(default=True, null=True, blank=True)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'], null=True)),
        ))
        db.send_create_signal('chroma_core', ['ManagedFilesystem'])

        # Adding model 'RemoveFilesystemJob'
        db.create_table('chroma_core_removefilesystemjob', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.Job'], unique=True, primary_key=True)),
            ('old_state', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('filesystem', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.ManagedFilesystem'])),
        ))
        db.send_create_signal('chroma_core', ['RemoveFilesystemJob'])

        # Adding model 'StartStoppedFilesystemJob'
        db.create_table('chroma_core_startstoppedfilesystemjob', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.Job'], unique=True, primary_key=True)),
            ('old_state', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('filesystem', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.ManagedFilesystem'])),
        ))
        db.send_create_signal('chroma_core', ['StartStoppedFilesystemJob'])

        # Adding model 'StartUnavailableFilesystemJob'
        db.create_table('chroma_core_startunavailablefilesystemjob', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.Job'], unique=True, primary_key=True)),
            ('old_state', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('filesystem', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.ManagedFilesystem'])),
        ))
        db.send_create_signal('chroma_core', ['StartUnavailableFilesystemJob'])

        # Adding model 'StopUnavailableFilesystemJob'
        db.create_table('chroma_core_stopunavailablefilesystemjob', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.Job'], unique=True, primary_key=True)),
            ('old_state', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('filesystem', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.ManagedFilesystem'])),
        ))
        db.send_create_signal('chroma_core', ['StopUnavailableFilesystemJob'])

        # Adding model 'MakeAvailableFilesystemUnavailable'
        db.create_table('chroma_core_makeavailablefilesystemunavailable', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.Job'], unique=True, primary_key=True)),
            ('old_state', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('filesystem', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.ManagedFilesystem'])),
        ))
        db.send_create_signal('chroma_core', ['MakeAvailableFilesystemUnavailable'])

        # Adding model 'ForgetFilesystemJob'
        db.create_table('chroma_core_forgetfilesystemjob', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.Job'], unique=True, primary_key=True)),
            ('old_state', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('filesystem', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.ManagedFilesystem'])),
        ))
        db.send_create_signal('chroma_core', ['ForgetFilesystemJob'])

        # Adding model 'ApplyConfParams'
        db.create_table('chroma_core_applyconfparams', (
            ('job_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.Job'], unique=True, primary_key=True)),
            ('mgs', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.ManagedMgs'])),
        ))
        db.send_create_signal('chroma_core', ['ApplyConfParams'])

        # Adding model 'ConfParam'
        db.create_table('chroma_core_confparam', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('mgs', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.ManagedMgs'])),
            ('key', self.gf('django.db.models.fields.CharField')(max_length=512)),
            ('value', self.gf('django.db.models.fields.CharField')(max_length=512, null=True, blank=True)),
            ('version', self.gf('django.db.models.fields.IntegerField')()),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'], null=True)),
        ))
        db.send_create_signal('chroma_core', ['ConfParam'])

        # Adding model 'FilesystemClientConfParam'
        db.create_table('chroma_core_filesystemclientconfparam', (
            ('confparam_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.ConfParam'], unique=True, primary_key=True)),
            ('filesystem', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.ManagedFilesystem'])),
        ))
        db.send_create_signal('chroma_core', ['FilesystemClientConfParam'])

        # Adding model 'FilesystemGlobalConfParam'
        db.create_table('chroma_core_filesystemglobalconfparam', (
            ('confparam_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.ConfParam'], unique=True, primary_key=True)),
            ('filesystem', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.ManagedFilesystem'])),
        ))
        db.send_create_signal('chroma_core', ['FilesystemGlobalConfParam'])

        # Adding model 'MdtConfParam'
        db.create_table('chroma_core_mdtconfparam', (
            ('confparam_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.ConfParam'], unique=True, primary_key=True)),
            ('mdt', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.ManagedMdt'])),
        ))
        db.send_create_signal('chroma_core', ['MdtConfParam'])

        # Adding model 'OstConfParam'
        db.create_table('chroma_core_ostconfparam', (
            ('confparam_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.ConfParam'], unique=True, primary_key=True)),
            ('ost', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.ManagedOst'])),
        ))
        db.send_create_signal('chroma_core', ['OstConfParam'])

        # Adding model 'StoragePluginRecord'
        db.create_table('chroma_core_storagepluginrecord', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('module_name', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('internal', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('chroma_core', ['StoragePluginRecord'])

        # Adding unique constraint on 'StoragePluginRecord', fields ['module_name']
        db.create_unique('chroma_core_storagepluginrecord', ['module_name'])

        # Adding model 'StorageResourceClass'
        db.create_table('chroma_core_storageresourceclass', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('storage_plugin', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.StoragePluginRecord'])),
            ('class_name', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('user_creatable', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('chroma_core', ['StorageResourceClass'])

        # Adding unique constraint on 'StorageResourceClass', fields ['storage_plugin', 'class_name']
        db.create_unique('chroma_core_storageresourceclass', ['storage_plugin_id', 'class_name'])

        # Adding model 'StorageResourceRecord'
        db.create_table('chroma_core_storageresourcerecord', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('resource_class', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.StorageResourceClass'])),
            ('storage_id_str', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('storage_id_scope', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.StorageResourceRecord'], null=True, blank=True)),
            ('alias', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
        ))
        db.send_create_signal('chroma_core', ['StorageResourceRecord'])

        # Adding unique constraint on 'StorageResourceRecord', fields ['storage_id_str', 'storage_id_scope', 'resource_class']
        db.create_unique('chroma_core_storageresourcerecord', ['storage_id_str', 'storage_id_scope_id', 'resource_class_id'])

        # Adding M2M table for field parents on 'StorageResourceRecord'
        db.create_table('chroma_core_storageresourcerecord_parents', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('from_storageresourcerecord', models.ForeignKey(orm['chroma_core.storageresourcerecord'], null=False)),
            ('to_storageresourcerecord', models.ForeignKey(orm['chroma_core.storageresourcerecord'], null=False))
        ))
        db.create_unique('chroma_core_storageresourcerecord_parents', ['from_storageresourcerecord_id', 'to_storageresourcerecord_id'])

        # Adding M2M table for field reported_by on 'StorageResourceRecord'
        db.create_table('chroma_core_storageresourcerecord_reported_by', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('from_storageresourcerecord', models.ForeignKey(orm['chroma_core.storageresourcerecord'], null=False)),
            ('to_storageresourcerecord', models.ForeignKey(orm['chroma_core.storageresourcerecord'], null=False))
        ))
        db.create_unique('chroma_core_storageresourcerecord_reported_by', ['from_storageresourcerecord_id', 'to_storageresourcerecord_id'])

        # Adding model 'SimpleHistoStoreBin'
        db.create_table('chroma_core_simplehistostorebin', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('histo_store_time', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.SimpleHistoStoreTime'])),
            ('bin_idx', self.gf('django.db.models.fields.IntegerField')()),
            ('value', self.gf('django.db.models.fields.PositiveIntegerField')()),
        ))
        db.send_create_signal('chroma_core', ['SimpleHistoStoreBin'])

        # Adding model 'SimpleHistoStoreTime'
        db.create_table('chroma_core_simplehistostoretime', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('storage_resource_statistic', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.StorageResourceStatistic'])),
            ('time', self.gf('django.db.models.fields.PositiveIntegerField')()),
        ))
        db.send_create_signal('chroma_core', ['SimpleHistoStoreTime'])

        # Adding model 'StorageResourceStatistic'
        db.create_table('chroma_core_storageresourcestatistic', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('storage_resource', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.StorageResourceRecord'])),
            ('sample_period', self.gf('django.db.models.fields.IntegerField')()),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=64)),
        ))
        db.send_create_signal('chroma_core', ['StorageResourceStatistic'])

        # Adding unique constraint on 'StorageResourceStatistic', fields ['storage_resource', 'name']
        db.create_unique('chroma_core_storageresourcestatistic', ['storage_resource_id', 'name'])

        # Adding model 'StorageResourceAttributeSerialized'
        db.create_table('chroma_core_storageresourceattributeserialized', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('resource', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.StorageResourceRecord'])),
            ('key', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('value', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('chroma_core', ['StorageResourceAttributeSerialized'])

        # Adding model 'StorageResourceAttributeReference'
        db.create_table('chroma_core_storageresourceattributereference', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('resource', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.StorageResourceRecord'])),
            ('key', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('value', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='value_resource', null=True, to=orm['chroma_core.StorageResourceRecord'])),
        ))
        db.send_create_signal('chroma_core', ['StorageResourceAttributeReference'])

        # Adding model 'StorageResourceClassStatistic'
        db.create_table('chroma_core_storageresourceclassstatistic', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('resource_class', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.StorageResourceClass'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=64)),
        ))
        db.send_create_signal('chroma_core', ['StorageResourceClassStatistic'])

        # Adding unique constraint on 'StorageResourceClassStatistic', fields ['resource_class', 'name']
        db.create_unique('chroma_core_storageresourceclassstatistic', ['resource_class_id', 'name'])

        # Adding model 'StorageResourceOffline'
        db.create_table('chroma_core_storageresourceoffline', (
            ('alertstate_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.AlertState'], unique=True, primary_key=True)),
        ))
        db.send_create_signal('chroma_core', ['StorageResourceOffline'])

        # Adding model 'StorageResourceAlert'
        db.create_table('chroma_core_storageresourcealert', (
            ('alertstate_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.AlertState'], unique=True, primary_key=True)),
            ('alert_class', self.gf('django.db.models.fields.CharField')(max_length=512)),
            ('attribute', self.gf('django.db.models.fields.CharField')(max_length=128, null=True, blank=True)),
        ))
        db.send_create_signal('chroma_core', ['StorageResourceAlert'])

        # Adding model 'StorageAlertPropagated'
        db.create_table('chroma_core_storagealertpropagated', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('storage_resource', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.StorageResourceRecord'])),
            ('alert_state', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.StorageResourceAlert'])),
        ))
        db.send_create_signal('chroma_core', ['StorageAlertPropagated'])

        # Adding unique constraint on 'StorageAlertPropagated', fields ['storage_resource', 'alert_state']
        db.create_unique('chroma_core_storagealertpropagated', ['storage_resource_id', 'alert_state_id'])

        # Adding model 'StorageResourceLearnEvent'
        db.create_table('chroma_core_storageresourcelearnevent', (
            ('event_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['chroma_core.Event'], unique=True, primary_key=True)),
            ('storage_resource', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.StorageResourceRecord'])),
        ))
        db.send_create_signal('chroma_core', ['StorageResourceLearnEvent'])

        # Adding model 'Systemevents'
        db.create_table(u'SystemEvents', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True, db_column='ID')),
            ('customerid', self.gf('django.db.models.fields.BigIntegerField')(null=True, db_column='CustomerID', blank=True)),
            ('receivedat', self.gf('chroma_core.models.utils.WorkaroundDateTimeField')(null=True, db_column='ReceivedAt', blank=True)),
            ('devicereportedtime', self.gf('chroma_core.models.utils.WorkaroundDateTimeField')(null=True, db_column='DeviceReportedTime', blank=True)),
            ('facility', self.gf('django.db.models.fields.IntegerField')(null=True, db_column='Facility', blank=True)),
            ('priority', self.gf('django.db.models.fields.IntegerField')(null=True, db_column='Priority', blank=True)),
            ('fromhost', self.gf('django.db.models.fields.CharField')(max_length=60, db_column='FromHost', blank=True)),
            ('message', self.gf('django.db.models.fields.TextField')(db_column='Message', blank=True)),
            ('ntseverity', self.gf('django.db.models.fields.IntegerField')(null=True, db_column='NTSeverity', blank=True)),
            ('importance', self.gf('django.db.models.fields.IntegerField')(null=True, db_column='Importance', blank=True)),
            ('eventsource', self.gf('django.db.models.fields.CharField')(max_length=60, db_column='EventSource', null=True, blank=True)),
            ('eventuser', self.gf('django.db.models.fields.CharField')(max_length=60, db_column='EventUser', null=True, blank=True)),
            ('eventcategory', self.gf('django.db.models.fields.IntegerField')(null=True, db_column='EventCategory', blank=True)),
            ('eventid', self.gf('django.db.models.fields.IntegerField')(null=True, db_column='EventID', blank=True)),
            ('eventbinarydata', self.gf('django.db.models.fields.TextField')(db_column='EventBinaryData', null=True, blank=True)),
            ('maxavailable', self.gf('django.db.models.fields.IntegerField')(null=True, db_column='MaxAvailable', blank=True)),
            ('currusage', self.gf('django.db.models.fields.IntegerField')(null=True, db_column='CurrUsage', blank=True)),
            ('minusage', self.gf('django.db.models.fields.IntegerField')(null=True, db_column='MinUsage', blank=True)),
            ('maxusage', self.gf('django.db.models.fields.IntegerField')(null=True, db_column='MaxUsage', blank=True)),
            ('infounitid', self.gf('django.db.models.fields.IntegerField')(null=True, db_column='InfoUnitID', blank=True)),
            ('syslogtag', self.gf('django.db.models.fields.CharField')(max_length=60, db_column='SysLogTag', null=True, blank=True)),
            ('eventlogtype', self.gf('django.db.models.fields.CharField')(max_length=60, db_column='EventLogType', null=True, blank=True)),
            ('genericfilename', self.gf('django.db.models.fields.CharField')(max_length=60, db_column='GenericFileName', null=True, blank=True)),
            ('systemid', self.gf('django.db.models.fields.IntegerField')(null=True, db_column='SystemID', blank=True)),
        ))
        db.send_create_signal('chroma_core', ['Systemevents'])

        # Adding model 'LastSystemeventsProcessed'
        db.create_table('chroma_core_lastsystemeventsprocessed', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('last', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal('chroma_core', ['LastSystemeventsProcessed'])

        # Adding model 'AgentSession'
        db.create_table('chroma_core_agentsession', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('host', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chroma_core.ManagedHost'])),
            ('session_id', self.gf('django.db.models.fields.CharField')(default='f7ad0b06', max_length=8)),
            ('counter', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal('chroma_core', ['AgentSession'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'StorageAlertPropagated', fields ['storage_resource', 'alert_state']
        db.delete_unique('chroma_core_storagealertpropagated', ['storage_resource_id', 'alert_state_id'])

        # Removing unique constraint on 'StorageResourceClassStatistic', fields ['resource_class', 'name']
        db.delete_unique('chroma_core_storageresourceclassstatistic', ['resource_class_id', 'name'])

        # Removing unique constraint on 'StorageResourceStatistic', fields ['storage_resource', 'name']
        db.delete_unique('chroma_core_storageresourcestatistic', ['storage_resource_id', 'name'])

        # Removing unique constraint on 'StorageResourceRecord', fields ['storage_id_str', 'storage_id_scope', 'resource_class']
        db.delete_unique('chroma_core_storageresourcerecord', ['storage_id_str', 'storage_id_scope_id', 'resource_class_id'])

        # Removing unique constraint on 'StorageResourceClass', fields ['storage_plugin', 'class_name']
        db.delete_unique('chroma_core_storageresourceclass', ['storage_plugin_id', 'class_name'])

        # Removing unique constraint on 'StoragePluginRecord', fields ['module_name']
        db.delete_unique('chroma_core_storagepluginrecord', ['module_name'])

        # Removing unique constraint on 'VolumeNode', fields ['host', 'path', 'not_deleted']
        db.delete_unique('chroma_core_volumenode', ['host_id', 'path', 'not_deleted'])

        # Removing unique constraint on 'Volume', fields ['storage_resource', 'not_deleted']
        db.delete_unique('chroma_core_volume', ['storage_resource_id', 'not_deleted'])

        # Removing unique constraint on 'ManagedHost', fields ['address', 'not_deleted']
        db.delete_unique('chroma_core_managedhost', ['address', 'not_deleted'])

        # Removing unique constraint on 'AlertState', fields ['alert_item_type', 'alert_item_id', 'alert_type', 'active']
        db.delete_unique('chroma_core_alertstate', ['alert_item_type_id', 'alert_item_id', 'alert_type', 'active'])

        # Deleting model 'Command'
        db.delete_table('chroma_core_command')

        # Removing M2M table for field jobs on 'Command'
        db.delete_table('chroma_core_command_jobs')

        # Deleting model 'Job'
        db.delete_table('chroma_core_job')

        # Deleting model 'StepResult'
        db.delete_table('chroma_core_stepresult')

        # Deleting model 'AlertState'
        db.delete_table('chroma_core_alertstate')

        # Deleting model 'AlertSubscription'
        db.delete_table('chroma_core_alertsubscription')

        # Deleting model 'AlertEmail'
        db.delete_table('chroma_core_alertemail')

        # Removing M2M table for field alerts on 'AlertEmail'
        db.delete_table('chroma_core_alertemail_alerts')

        # Deleting model 'Event'
        db.delete_table('chroma_core_event')

        # Deleting model 'LearnEvent'
        db.delete_table('chroma_core_learnevent')

        # Deleting model 'AlertEvent'
        db.delete_table('chroma_core_alertevent')

        # Deleting model 'SyslogEvent'
        db.delete_table('chroma_core_syslogevent')

        # Deleting model 'ClientConnectEvent'
        db.delete_table('chroma_core_clientconnectevent')

        # Deleting model 'ManagedHost'
        db.delete_table('chroma_core_managedhost')

        # Deleting model 'Volume'
        db.delete_table('chroma_core_volume')

        # Deleting model 'VolumeNode'
        db.delete_table('chroma_core_volumenode')

        # Deleting model 'LNetConfiguration'
        db.delete_table('chroma_core_lnetconfiguration')

        # Deleting model 'Nid'
        db.delete_table('chroma_core_nid')

        # Deleting model 'ConfigureLNetJob'
        db.delete_table('chroma_core_configurelnetjob')

        # Deleting model 'GetLNetStateJob'
        db.delete_table('chroma_core_getlnetstatejob')

        # Deleting model 'SetupHostJob'
        db.delete_table('chroma_core_setuphostjob')

        # Deleting model 'EnableLNetJob'
        db.delete_table('chroma_core_enablelnetjob')

        # Deleting model 'DetectTargetsJob'
        db.delete_table('chroma_core_detecttargetsjob')

        # Deleting model 'LoadLNetJob'
        db.delete_table('chroma_core_loadlnetjob')

        # Deleting model 'UnloadLNetJob'
        db.delete_table('chroma_core_unloadlnetjob')

        # Deleting model 'StartLNetJob'
        db.delete_table('chroma_core_startlnetjob')

        # Deleting model 'StopLNetJob'
        db.delete_table('chroma_core_stoplnetjob')

        # Deleting model 'RemoveHostJob'
        db.delete_table('chroma_core_removehostjob')

        # Deleting model 'ForceRemoveHostJob'
        db.delete_table('chroma_core_forceremovehostjob')

        # Deleting model 'RemoveUnconfiguredHostJob'
        db.delete_table('chroma_core_removeunconfiguredhostjob')

        # Deleting model 'RelearnNidsJob'
        db.delete_table('chroma_core_relearnnidsjob')

        # Deleting model 'UpdateNidsJob'
        db.delete_table('chroma_core_updatenidsjob')

        # Deleting model 'HostContactAlert'
        db.delete_table('chroma_core_hostcontactalert')

        # Deleting model 'LNetOfflineAlert'
        db.delete_table('chroma_core_lnetofflinealert')

        # Deleting model 'LNetNidsChangedAlert'
        db.delete_table('chroma_core_lnetnidschangedalert')

        # Deleting model 'ManagedTarget'
        db.delete_table('chroma_core_managedtarget')

        # Deleting model 'ManagedOst'
        db.delete_table('chroma_core_managedost')

        # Deleting model 'ManagedMdt'
        db.delete_table('chroma_core_managedmdt')

        # Deleting model 'ManagedMgs'
        db.delete_table('chroma_core_managedmgs')

        # Deleting model 'TargetRecoveryInfo'
        db.delete_table('chroma_core_targetrecoveryinfo')

        # Deleting model 'RemoveConfiguredTargetJob'
        db.delete_table('chroma_core_removeconfiguredtargetjob')

        # Deleting model 'RemoveTargetJob'
        db.delete_table('chroma_core_removetargetjob')

        # Deleting model 'ForgetTargetJob'
        db.delete_table('chroma_core_forgettargetjob')

        # Deleting model 'ConfigureTargetJob'
        db.delete_table('chroma_core_configuretargetjob')

        # Deleting model 'RegisterTargetJob'
        db.delete_table('chroma_core_registertargetjob')

        # Deleting model 'StartTargetJob'
        db.delete_table('chroma_core_starttargetjob')

        # Deleting model 'StopTargetJob'
        db.delete_table('chroma_core_stoptargetjob')

        # Deleting model 'FormatTargetJob'
        db.delete_table('chroma_core_formattargetjob')

        # Deleting model 'ManagedTargetMount'
        db.delete_table('chroma_core_managedtargetmount')

        # Deleting model 'TargetOfflineAlert'
        db.delete_table('chroma_core_targetofflinealert')

        # Deleting model 'TargetFailoverAlert'
        db.delete_table('chroma_core_targetfailoveralert')

        # Deleting model 'TargetRecoveryAlert'
        db.delete_table('chroma_core_targetrecoveryalert')

        # Deleting model 'ManagedFilesystem'
        db.delete_table('chroma_core_managedfilesystem')

        # Deleting model 'RemoveFilesystemJob'
        db.delete_table('chroma_core_removefilesystemjob')

        # Deleting model 'StartStoppedFilesystemJob'
        db.delete_table('chroma_core_startstoppedfilesystemjob')

        # Deleting model 'StartUnavailableFilesystemJob'
        db.delete_table('chroma_core_startunavailablefilesystemjob')

        # Deleting model 'StopUnavailableFilesystemJob'
        db.delete_table('chroma_core_stopunavailablefilesystemjob')

        # Deleting model 'MakeAvailableFilesystemUnavailable'
        db.delete_table('chroma_core_makeavailablefilesystemunavailable')

        # Deleting model 'ForgetFilesystemJob'
        db.delete_table('chroma_core_forgetfilesystemjob')

        # Deleting model 'ApplyConfParams'
        db.delete_table('chroma_core_applyconfparams')

        # Deleting model 'ConfParam'
        db.delete_table('chroma_core_confparam')

        # Deleting model 'FilesystemClientConfParam'
        db.delete_table('chroma_core_filesystemclientconfparam')

        # Deleting model 'FilesystemGlobalConfParam'
        db.delete_table('chroma_core_filesystemglobalconfparam')

        # Deleting model 'MdtConfParam'
        db.delete_table('chroma_core_mdtconfparam')

        # Deleting model 'OstConfParam'
        db.delete_table('chroma_core_ostconfparam')

        # Deleting model 'StoragePluginRecord'
        db.delete_table('chroma_core_storagepluginrecord')

        # Deleting model 'StorageResourceClass'
        db.delete_table('chroma_core_storageresourceclass')

        # Deleting model 'StorageResourceRecord'
        db.delete_table('chroma_core_storageresourcerecord')

        # Removing M2M table for field parents on 'StorageResourceRecord'
        db.delete_table('chroma_core_storageresourcerecord_parents')

        # Removing M2M table for field reported_by on 'StorageResourceRecord'
        db.delete_table('chroma_core_storageresourcerecord_reported_by')

        # Deleting model 'SimpleHistoStoreBin'
        db.delete_table('chroma_core_simplehistostorebin')

        # Deleting model 'SimpleHistoStoreTime'
        db.delete_table('chroma_core_simplehistostoretime')

        # Deleting model 'StorageResourceStatistic'
        db.delete_table('chroma_core_storageresourcestatistic')

        # Deleting model 'StorageResourceAttributeSerialized'
        db.delete_table('chroma_core_storageresourceattributeserialized')

        # Deleting model 'StorageResourceAttributeReference'
        db.delete_table('chroma_core_storageresourceattributereference')

        # Deleting model 'StorageResourceClassStatistic'
        db.delete_table('chroma_core_storageresourceclassstatistic')

        # Deleting model 'StorageResourceOffline'
        db.delete_table('chroma_core_storageresourceoffline')

        # Deleting model 'StorageResourceAlert'
        db.delete_table('chroma_core_storageresourcealert')

        # Deleting model 'StorageAlertPropagated'
        db.delete_table('chroma_core_storagealertpropagated')

        # Deleting model 'StorageResourceLearnEvent'
        db.delete_table('chroma_core_storageresourcelearnevent')

        # Deleting model 'Systemevents'
        db.delete_table(u'SystemEvents')

        # Deleting model 'LastSystemeventsProcessed'
        db.delete_table('chroma_core_lastsystemeventsprocessed')

        # Deleting model 'AgentSession'
        db.delete_table('chroma_core_agentsession')


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
        'chroma_core.agentsession': {
            'Meta': {'object_name': 'AgentSession'},
            'counter': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'session_id': ('django.db.models.fields.CharField', [], {'default': "'b04627f2'", 'max_length': '8'})
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
            'begin': ('chroma_core.models.utils.WorkaroundDateTimeField', [], {}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'dismissed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'end': ('chroma_core.models.utils.WorkaroundDateTimeField', [], {}),
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
            'created_at': ('chroma_core.models.utils.WorkaroundDateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
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
            'created_at': ('chroma_core.models.utils.WorkaroundDateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
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
            'created_at': ('chroma_core.models.utils.WorkaroundDateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'errored': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'finished_step': ('django.db.models.fields.PositiveIntegerField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'locks_json': ('django.db.models.fields.TextField', [], {}),
            'modified_at': ('chroma_core.models.utils.WorkaroundDateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'paused': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'started_step': ('django.db.models.fields.PositiveIntegerField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'default': "'pending'", 'max_length': '16'}),
            'task_id': ('django.db.models.fields.CharField', [], {'max_length': '36', 'null': 'True', 'blank': 'True'}),
            'wait_for_json': ('django.db.models.fields.TextField', [], {})
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
            'immutable_state': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'state_modified_at': ('chroma_core.models.utils.WorkaroundDateTimeField', [], {})
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
            'mgs': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedMgs']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '8'}),
            'not_deleted': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'state_modified_at': ('chroma_core.models.utils.WorkaroundDateTimeField', [], {})
        },
        'chroma_core.managedhost': {
            'Meta': {'unique_together': "(('address', 'not_deleted'),)", 'object_name': 'ManagedHost'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'agent_token': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'fqdn': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'immutable_state': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_contact': ('chroma_core.models.utils.WorkaroundDateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'nodename': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'not_deleted': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'state_modified_at': ('chroma_core.models.utils.WorkaroundDateTimeField', [], {})
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
            'state_modified_at': ('chroma_core.models.utils.WorkaroundDateTimeField', [], {}),
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
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
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
            'created_at': ('chroma_core.models.utils.WorkaroundDateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'exception': ('picklefield.fields.PickledObjectField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.Job']"}),
            'modified_at': ('chroma_core.models.utils.WorkaroundDateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
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
            'value': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'value_resource'", 'null': 'True', 'to': "orm['chroma_core.StorageResourceRecord']"})
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
            'storage_plugin': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.StoragePluginRecord']"}),
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
            'storage_resource': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.StorageResourceRecord']"})
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
            'devicereportedtime': ('chroma_core.models.utils.WorkaroundDateTimeField', [], {'null': 'True', 'db_column': "'DeviceReportedTime'", 'blank': 'True'}),
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
            'receivedat': ('chroma_core.models.utils.WorkaroundDateTimeField', [], {'null': 'True', 'db_column': "'ReceivedAt'", 'blank': 'True'}),
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
            'Meta': {'object_name': 'UnloadLNetJob'},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.updatenidsjob': {
            'Meta': {'object_name': 'UpdateNidsJob', '_ormbases': ['chroma_core.Job']},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.volume': {
            'Meta': {'unique_together': "(('storage_resource', 'not_deleted'),)", 'object_name': 'Volume'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'not_deleted': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'size': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'storage_resource': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.StorageResourceRecord']", 'null': 'True', 'blank': 'True'})
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
