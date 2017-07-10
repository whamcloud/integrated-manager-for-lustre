# -*- coding: utf-8 -*-
import datetime
import django
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'StorageResourceClassStatistic.modified_at'
        db.add_column('chroma_core_storageresourceclassstatistic', 'modified_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=django.utils.timezone.now, blank=True),
                      keep_default=False)

        # Adding field 'PackageVersion.modified_at'
        db.add_column('chroma_core_packageversion', 'modified_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=django.utils.timezone.now, blank=True),
                      keep_default=False)

        # Adding field 'AlertEmail.modified_at'
        db.add_column('chroma_core_alertemail', 'modified_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=django.utils.timezone.now, blank=True),
                      keep_default=False)

        # Adding field 'Copytool.modified_at'
        db.add_column('chroma_core_copytool', 'modified_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=django.utils.timezone.now, blank=True),
                      keep_default=False)

        # Adding field 'StorageResourceClass.modified_at'
        db.add_column('chroma_core_storageresourceclass', 'modified_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=django.utils.timezone.now, blank=True),
                      keep_default=False)

        # Adding field 'RSyslogConfiguration.modified_at'
        db.add_column('chroma_core_rsyslogconfiguration', 'modified_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=django.utils.timezone.now, blank=True),
                      keep_default=False)

        # Adding field 'ServerProfileValidation.modified_at'
        db.add_column('chroma_core_serverprofilevalidation', 'modified_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=django.utils.timezone.now, blank=True),
                      keep_default=False)

        # Adding field 'ManagedTarget.modified_at'
        db.add_column('chroma_core_managedtarget', 'modified_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=django.utils.timezone.now, blank=True),
                      keep_default=False)

        # Adding field 'PackageInstallation.modified_at'
        db.add_column('chroma_core_packageinstallation', 'modified_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=django.utils.timezone.now, blank=True),
                      keep_default=False)

        # Adding field 'Command.modified_at'
        db.add_column('chroma_core_command', 'modified_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=django.utils.timezone.now, blank=True),
                      keep_default=False)

        # Adding field 'ManagedFilesystem.modified_at'
        db.add_column('chroma_core_managedfilesystem', 'modified_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=django.utils.timezone.now, blank=True),
                      keep_default=False)

        # Adding field 'PacemakerConfiguration.modified_at'
        db.add_column('chroma_core_pacemakerconfiguration', 'modified_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=django.utils.timezone.now, blank=True),
                      keep_default=False)

        # Adding field 'PowerControlType.modified_at'
        db.add_column('chroma_core_powercontroltype', 'modified_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=django.utils.timezone.now, blank=True),
                      keep_default=False)


        # Adding field 'AlertSubscription.modified_at'
        db.add_column('chroma_core_alertsubscription', 'modified_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=django.utils.timezone.now, blank=True),
                      keep_default=False)

        # Adding field 'StorageAlertPropagated.modified_at'
        db.add_column('chroma_core_storagealertpropagated', 'modified_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=django.utils.timezone.now, blank=True),
                      keep_default=False)

        # Adding field 'ManagedTargetMount.modified_at'
        db.add_column('chroma_core_managedtargetmount', 'modified_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=django.utils.timezone.now, blank=True),
                      keep_default=False)

        # Adding field 'Nid.modified_at'
        db.add_column('chroma_core_nid', 'modified_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=django.utils.timezone.now, blank=True),
                      keep_default=False)

        # Adding field 'NTPConfiguration.modified_at'
        db.add_column('chroma_core_ntpconfiguration', 'modified_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=django.utils.timezone.now, blank=True),
                      keep_default=False)

        # Adding field 'ClientCertificate.modified_at'
        db.add_column('chroma_core_clientcertificate', 'modified_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=django.utils.timezone.now, blank=True),
                      keep_default=False)

        # Adding field 'AlertState.modified_at'
        db.add_column('chroma_core_alertstate', 'modified_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=django.utils.timezone.now, blank=True),
                      keep_default=False)

        # Adding field 'CopytoolOperation.modified_at'
        db.add_column('chroma_core_copytooloperation', 'modified_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=django.utils.timezone.now, blank=True),
                      keep_default=False)

        # Adding field 'VolumeNode.modified_at'
        db.add_column('chroma_core_volumenode', 'modified_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=django.utils.timezone.now, blank=True),
                      keep_default=False)

        # Adding field 'PackageAvailability.modified_at'
        db.add_column('chroma_core_packageavailability', 'modified_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=django.utils.timezone.now, blank=True),
                      keep_default=False)

        # Adding field 'UserProfile.modified_at'
        db.add_column('chroma_core_userprofile', 'modified_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=django.utils.timezone.now, blank=True),
                      keep_default=False)

        # Adding field 'Bundle.modified_at'
        db.add_column('chroma_core_bundle', 'modified_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=django.utils.timezone.now, blank=True),
                      keep_default=False)

        # Adding field 'LogMessage.modified_at'
        db.add_column('chroma_core_logmessage', 'modified_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=django.utils.timezone.now, blank=True),
                      keep_default=False)

        # Adding field 'ManagedHost.modified_at'
        db.add_column('chroma_core_managedhost', 'modified_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=django.utils.timezone.now, blank=True),
                      keep_default=False)

        # Adding field 'ServerProfile.modified_at'
        db.add_column('chroma_core_serverprofile', 'modified_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=django.utils.timezone.now, blank=True),
                      keep_default=False)

        # Adding field 'PowerControlDeviceOutlet.modified_at'
        db.add_column('chroma_core_powercontroldeviceoutlet', 'modified_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=django.utils.timezone.now, blank=True),
                      keep_default=False)

        # Adding field 'CorosyncConfiguration.modified_at'
        db.add_column('chroma_core_corosyncconfiguration', 'modified_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=django.utils.timezone.now, blank=True),
                      keep_default=False)

        # Adding field 'LustreClientMount.modified_at'
        db.add_column('chroma_core_lustreclientmount', 'modified_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=django.utils.timezone.now, blank=True),
                      keep_default=False)

        # Adding field 'StorageResourceAttributeSerialized.modified_at'
        db.add_column('chroma_core_storageresourceattributeserialized', 'modified_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=django.utils.timezone.now, blank=True),
                      keep_default=False)

        # Adding field 'RegistrationToken.modified_at'
        db.add_column('chroma_core_registrationtoken', 'modified_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=django.utils.timezone.now, blank=True),
                      keep_default=False)

        # Adding field 'StoragePluginRecord.modified_at'
        db.add_column('chroma_core_storagepluginrecord', 'modified_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=django.utils.timezone.now, blank=True),
                      keep_default=False)

        # Adding field 'ServerProfilePackage.modified_at'
        db.add_column('chroma_core_serverprofilepackage', 'modified_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=django.utils.timezone.now, blank=True),
                      keep_default=False)

        # Adding field 'Volume.modified_at'
        db.add_column('chroma_core_volume', 'modified_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=django.utils.timezone.now, blank=True),
                      keep_default=False)

        # Adding field 'PowerControlDevice.modified_at'
        db.add_column('chroma_core_powercontroldevice', 'modified_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=django.utils.timezone.now, blank=True),
                      keep_default=False)

        # Adding field 'StorageResourceRecord.modified_at'
        db.add_column('chroma_core_storageresourcerecord', 'modified_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=django.utils.timezone.now, blank=True),
                      keep_default=False)

        # Adding field 'Package.modified_at'
        db.add_column('chroma_core_package', 'modified_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=django.utils.timezone.now, blank=True),
                      keep_default=False)

        # Adding field 'StorageResourceAttributeReference.modified_at'
        db.add_column('chroma_core_storageresourceattributereference', 'modified_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=django.utils.timezone.now, blank=True),
                      keep_default=False)

        # Adding field 'LNetConfiguration.modified_at'
        db.add_column('chroma_core_lnetconfiguration', 'modified_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=django.utils.timezone.now, blank=True),
                      keep_default=False)

        # Adding field 'ConfParam.modified_at'
        db.add_column('chroma_core_confparam', 'modified_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=django.utils.timezone.now, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'StorageResourceClassStatistic.modified_at'
        db.delete_column('chroma_core_storageresourceclassstatistic', 'modified_at')

        # Deleting field 'PackageVersion.modified_at'
        db.delete_column('chroma_core_packageversion', 'modified_at')

        # Deleting field 'AlertEmail.modified_at'
        db.delete_column('chroma_core_alertemail', 'modified_at')

        # Deleting field 'Copytool.modified_at'
        db.delete_column('chroma_core_copytool', 'modified_at')

        # Deleting field 'StorageResourceClass.modified_at'
        db.delete_column('chroma_core_storageresourceclass', 'modified_at')

        # Deleting field 'RSyslogConfiguration.modified_at'
        db.delete_column('chroma_core_rsyslogconfiguration', 'modified_at')

        # Deleting field 'ServerProfileValidation.modified_at'
        db.delete_column('chroma_core_serverprofilevalidation', 'modified_at')

        # Deleting field 'ManagedTarget.modified_at'
        db.delete_column('chroma_core_managedtarget', 'modified_at')

        # Deleting field 'PackageInstallation.modified_at'
        db.delete_column('chroma_core_packageinstallation', 'modified_at')

        # Deleting field 'Command.modified_at'
        db.delete_column('chroma_core_command', 'modified_at')

        # Deleting field 'ManagedFilesystem.modified_at'
        db.delete_column('chroma_core_managedfilesystem', 'modified_at')

        # Deleting field 'PacemakerConfiguration.modified_at'
        db.delete_column('chroma_core_pacemakerconfiguration', 'modified_at')

        # Deleting field 'PowerControlType.modified_at'
        db.delete_column('chroma_core_powercontroltype', 'modified_at')

        # Deleting field 'AlertSubscription.modified_at'
        db.delete_column('chroma_core_alertsubscription', 'modified_at')

        # Deleting field 'StorageAlertPropagated.modified_at'
        db.delete_column('chroma_core_storagealertpropagated', 'modified_at')

        # Deleting field 'ManagedTargetMount.modified_at'
        db.delete_column('chroma_core_managedtargetmount', 'modified_at')

        # Deleting field 'Nid.modified_at'
        db.delete_column('chroma_core_nid', 'modified_at')

        # Deleting field 'NTPConfiguration.modified_at'
        db.delete_column('chroma_core_ntpconfiguration', 'modified_at')

        # Deleting field 'ClientCertificate.modified_at'
        db.delete_column('chroma_core_clientcertificate', 'modified_at')

        # Deleting field 'AlertState.modified_at'
        db.delete_column('chroma_core_alertstate', 'modified_at')

        # Deleting field 'CopytoolOperation.modified_at'
        db.delete_column('chroma_core_copytooloperation', 'modified_at')

        # Deleting field 'VolumeNode.modified_at'
        db.delete_column('chroma_core_volumenode', 'modified_at')

        # Deleting field 'PackageAvailability.modified_at'
        db.delete_column('chroma_core_packageavailability', 'modified_at')

        # Deleting field 'UserProfile.modified_at'
        db.delete_column('chroma_core_userprofile', 'modified_at')

        # Deleting field 'Bundle.modified_at'
        db.delete_column('chroma_core_bundle', 'modified_at')

        # Deleting field 'LogMessage.modified_at'
        db.delete_column('chroma_core_logmessage', 'modified_at')

        # Deleting field 'ManagedHost.modified_at'
        db.delete_column('chroma_core_managedhost', 'modified_at')

        # Deleting field 'ServerProfile.modified_at'
        db.delete_column('chroma_core_serverprofile', 'modified_at')

        # Deleting field 'PowerControlDeviceOutlet.modified_at'
        db.delete_column('chroma_core_powercontroldeviceoutlet', 'modified_at')

        # Deleting field 'CorosyncConfiguration.modified_at'
        db.delete_column('chroma_core_corosyncconfiguration', 'modified_at')

        # Deleting field 'LustreClientMount.modified_at'
        db.delete_column('chroma_core_lustreclientmount', 'modified_at')

        # Deleting field 'StorageResourceAttributeSerialized.modified_at'
        db.delete_column('chroma_core_storageresourceattributeserialized', 'modified_at')

        # Deleting field 'RegistrationToken.modified_at'
        db.delete_column('chroma_core_registrationtoken', 'modified_at')

        # Deleting field 'StoragePluginRecord.modified_at'
        db.delete_column('chroma_core_storagepluginrecord', 'modified_at')

        # Deleting field 'ServerProfilePackage.modified_at'
        db.delete_column('chroma_core_serverprofilepackage', 'modified_at')

        # Deleting field 'Volume.modified_at'
        db.delete_column('chroma_core_volume', 'modified_at')

        # Deleting field 'PowerControlDevice.modified_at'
        db.delete_column('chroma_core_powercontroldevice', 'modified_at')

        # Deleting field 'StorageResourceRecord.modified_at'
        db.delete_column('chroma_core_storageresourcerecord', 'modified_at')

        # Deleting field 'Package.modified_at'
        db.delete_column('chroma_core_package', 'modified_at')

        # Deleting field 'StorageResourceAttributeReference.modified_at'
        db.delete_column('chroma_core_storageresourceattributereference', 'modified_at')

        # Deleting field 'LNetConfiguration.modified_at'
        db.delete_column('chroma_core_lnetconfiguration', 'modified_at')

        # Deleting field 'ConfParam.modified_at'
        db.delete_column('chroma_core_confparam', 'modified_at')


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
            'Meta': {'ordering': "['id']", 'object_name': 'AlertEmail'},
            'alerts': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['chroma_core.AlertState']", 'symmetrical': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'chroma_core.alertevent': {
            'Meta': {'object_name': 'AlertEvent', 'db_table': "'chroma_core_alertstate'"},
            '_message': ('django.db.models.fields.TextField', [], {'null': 'True', 'db_column': "'message'"}),
            'active': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'alert_item_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'alert_item_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'alert_type': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'begin': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'dismissed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'end': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lustre_pid': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'record_type': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128'}),
            'severity': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'variant': ('django.db.models.fields.CharField', [], {'default': "'{}'", 'max_length': '512'})
        },
        'chroma_core.alertstate': {
            'Meta': {'object_name': 'AlertState'},
            '_message': ('django.db.models.fields.TextField', [], {'null': 'True', 'db_column': "'message'"}),
            'active': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'alert_item_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'alert_item_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'alert_type': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'begin': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'dismissed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'end': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lustre_pid': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'record_type': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128'}),
            'severity': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'variant': ('django.db.models.fields.CharField', [], {'default': "'{}'", 'max_length': '512'})
        },
        'chroma_core.alertsubscription': {
            'Meta': {'ordering': "['id']", 'object_name': 'AlertSubscription'},
            'alert_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'alert_subscriptions'", 'to': "orm['auth.User']"})
        },
        'chroma_core.applyconfparams': {
            'Meta': {'ordering': "['id']", 'object_name': 'ApplyConfParams', '_ormbases': ['chroma_core.Job']},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'mgs': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedTarget']"})
        },
        'chroma_core.autoconfigurecorosync2job': {
            'Meta': {'ordering': "['id']", 'object_name': 'AutoConfigureCorosync2Job'},
            'corosync_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.Corosync2Configuration']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.autoconfigurecorosyncjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'AutoConfigureCorosyncJob'},
            'corosync_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.CorosyncConfiguration']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.bundle': {
            'Meta': {'unique_together': "(('bundle_name',),)", 'object_name': 'Bundle'},
            'bundle_name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'primary_key': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'location': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'version': ('django.db.models.fields.CharField', [], {'default': "'0.0.0'", 'max_length': '255'})
        },
        'chroma_core.clientcertificate': {
            'Meta': {'object_name': 'ClientCertificate'},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'revoked': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'serial': ('django.db.models.fields.CharField', [], {'max_length': '16'})
        },
        'chroma_core.clientconnectevent': {
            'Meta': {'object_name': 'ClientConnectEvent', 'db_table': "'chroma_core_alertstate'"},
            '_message': ('django.db.models.fields.TextField', [], {'null': 'True', 'db_column': "'message'"}),
            'active': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'alert_item_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'alert_item_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'alert_type': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'begin': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'dismissed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'end': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lustre_pid': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'record_type': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128'}),
            'severity': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'variant': ('django.db.models.fields.CharField', [], {'default': "'{}'", 'max_length': '512'})
        },
        'chroma_core.command': {
            'Meta': {'ordering': "['id']", 'object_name': 'Command'},
            'cancelled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'complete': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'errored': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'jobs': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['chroma_core.Job']", 'symmetrical': 'False'}),
            'message': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'chroma_core.commandcancelledalert': {
            'Meta': {'object_name': 'CommandCancelledAlert', 'db_table': "'chroma_core_alertstate'"},
            '_message': ('django.db.models.fields.TextField', [], {'null': 'True', 'db_column': "'message'"}),
            'active': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'alert_item_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'alert_item_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'alert_type': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'begin': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'dismissed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'end': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lustre_pid': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'record_type': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128'}),
            'severity': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'variant': ('django.db.models.fields.CharField', [], {'default': "'{}'", 'max_length': '512'})
        },
        'chroma_core.commanderroredalert': {
            'Meta': {'object_name': 'CommandErroredAlert', 'db_table': "'chroma_core_alertstate'"},
            '_message': ('django.db.models.fields.TextField', [], {'null': 'True', 'db_column': "'message'"}),
            'active': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'alert_item_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'alert_item_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'alert_type': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'begin': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'dismissed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'end': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lustre_pid': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'record_type': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128'}),
            'severity': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'variant': ('django.db.models.fields.CharField', [], {'default': "'{}'", 'max_length': '512'})
        },
        'chroma_core.commandrunningalert': {
            'Meta': {'object_name': 'CommandRunningAlert', 'db_table': "'chroma_core_alertstate'"},
            '_message': ('django.db.models.fields.TextField', [], {'null': 'True', 'db_column': "'message'"}),
            'active': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'alert_item_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'alert_item_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'alert_type': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'begin': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'dismissed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'end': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lustre_pid': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'record_type': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128'}),
            'severity': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'variant': ('django.db.models.fields.CharField', [], {'default': "'{}'", 'max_length': '512'})
        },
        'chroma_core.commandsuccessfulalert': {
            'Meta': {'object_name': 'CommandSuccessfulAlert', 'db_table': "'chroma_core_alertstate'"},
            '_message': ('django.db.models.fields.TextField', [], {'null': 'True', 'db_column': "'message'"}),
            'active': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'alert_item_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'alert_item_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'alert_type': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'begin': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'dismissed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'end': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lustre_pid': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'record_type': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128'}),
            'severity': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'variant': ('django.db.models.fields.CharField', [], {'default': "'{}'", 'max_length': '512'})
        },
        'chroma_core.configurecopytooljob': {
            'Meta': {'ordering': "['id']", 'object_name': 'ConfigureCopytoolJob'},
            'copytool': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.Copytool']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.configurecorosync2job': {
            'Meta': {'ordering': "['id']", 'object_name': 'ConfigureCorosync2Job'},
            'corosync_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.Corosync2Configuration']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'mcast_port': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'network_interface_0': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': "orm['chroma_core.NetworkInterface']"}),
            'network_interface_1': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': "orm['chroma_core.NetworkInterface']"})
        },
        'chroma_core.configurecorosyncjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'ConfigureCorosyncJob'},
            'corosync_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.CorosyncConfiguration']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'mcast_port': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'network_interface_0': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': "orm['chroma_core.NetworkInterface']"}),
            'network_interface_1': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': "orm['chroma_core.NetworkInterface']"})
        },
        'chroma_core.configurehostfencingjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'ConfigureHostFencingJob', '_ormbases': ['chroma_core.Job']},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.configurelnetjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'ConfigureLNetJob', '_ormbases': ['chroma_core.Job']},
            'config_changes': ('django.db.models.fields.CharField', [], {'max_length': '4096'}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'lnet_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.LNetConfiguration']"})
        },
        'chroma_core.configurentpjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'ConfigureNTPJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'ntp_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.NTPConfiguration']"}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.configurepacemakerjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'ConfigurePacemakerJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'pacemaker_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.PacemakerConfiguration']"})
        },
        'chroma_core.configurersyslogjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'ConfigureRsyslogJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'rsyslog_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.RSyslogConfiguration']"})
        },
        'chroma_core.configuretargetjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'ConfigureTargetJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedTarget']"})
        },
        'chroma_core.confparam': {
            'Meta': {'ordering': "['id']", 'object_name': 'ConfParam'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'mgs': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedMgs']"}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '512', 'null': 'True', 'blank': 'True'}),
            'version': ('django.db.models.fields.IntegerField', [], {})
        },
        'chroma_core.copytool': {
            'Meta': {'ordering': "['id']", 'unique_together': "(('host', 'bin_path', 'filesystem', 'archive', 'index', 'not_deleted'),)", 'object_name': 'Copytool'},
            'archive': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'bin_path': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'client_mount': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'copytools'", 'null': 'True', 'to': "orm['chroma_core.LustreClientMount']"}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'filesystem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedFilesystem']"}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'copytools'", 'to': "orm['chroma_core.ManagedHost']"}),
            'hsm_arguments': ('django.db.models.fields.CharField', [], {'max_length': '131072'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'immutable_state': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'index': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'mountpoint': ('django.db.models.fields.CharField', [], {'default': "'/mnt/lustre'", 'max_length': '1024'}),
            'not_deleted': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'pid': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'state_modified_at': ('django.db.models.fields.DateTimeField', [], {}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '36', 'null': 'True', 'blank': 'True'})
        },
        'chroma_core.copytooloperation': {
            'Meta': {'ordering': "['id']", 'unique_together': "(('state', 'copytool', 'fid', 'started_at', 'finished_at'),)", 'object_name': 'CopytoolOperation'},
            'copytool': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'operations'", 'to': "orm['chroma_core.Copytool']"}),
            'fid': ('django.db.models.fields.CharField', [], {'max_length': '1024', 'null': 'True', 'blank': 'True'}),
            'finished_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'info': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'path': ('django.db.models.fields.CharField', [], {'max_length': '1024', 'null': 'True', 'blank': 'True'}),
            'processed_bytes': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'started_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'total_bytes': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        'chroma_core.corosync2configuration': {
            'Meta': {'ordering': "['id']", 'object_name': 'Corosync2Configuration', '_ormbases': ['chroma_core.CorosyncConfiguration']},
            'corosyncconfiguration_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.CorosyncConfiguration']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.corosyncconfiguration': {
            'Meta': {'ordering': "['id']", 'object_name': 'CorosyncConfiguration'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'corosync_reported_up': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'host': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'_corosync_configuration'", 'unique': 'True', 'to': "orm['chroma_core.ManagedHost']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'immutable_state': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'mcast_port': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'not_deleted': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'record_type': ('django.db.models.fields.CharField', [], {'default': "'CorosyncConfiguration'", 'max_length': '128'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'state_modified_at': ('django.db.models.fields.DateTimeField', [], {})
        },
        'chroma_core.corosyncnopeersalert': {
            'Meta': {'object_name': 'CorosyncNoPeersAlert', 'db_table': "'chroma_core_alertstate'"},
            '_message': ('django.db.models.fields.TextField', [], {'null': 'True', 'db_column': "'message'"}),
            'active': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'alert_item_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'alert_item_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'alert_type': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'begin': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'dismissed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'end': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lustre_pid': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'record_type': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128'}),
            'severity': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'variant': ('django.db.models.fields.CharField', [], {'default': "'{}'", 'max_length': '512'})
        },
        'chroma_core.corosyncstoppedalert': {
            'Meta': {'object_name': 'CorosyncStoppedAlert', 'db_table': "'chroma_core_alertstate'"},
            '_message': ('django.db.models.fields.TextField', [], {'null': 'True', 'db_column': "'message'"}),
            'active': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'alert_item_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'alert_item_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'alert_type': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'begin': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'dismissed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'end': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lustre_pid': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'record_type': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128'}),
            'severity': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'variant': ('django.db.models.fields.CharField', [], {'default': "'{}'", 'max_length': '512'})
        },
        'chroma_core.corosynctomanypeersalert': {
            'Meta': {'object_name': 'CorosyncToManyPeersAlert', 'db_table': "'chroma_core_alertstate'"},
            '_message': ('django.db.models.fields.TextField', [], {'null': 'True', 'db_column': "'message'"}),
            'active': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'alert_item_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'alert_item_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'alert_type': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'begin': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'dismissed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'end': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lustre_pid': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'record_type': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128'}),
            'severity': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'variant': ('django.db.models.fields.CharField', [], {'default': "'{}'", 'max_length': '512'})
        },
        'chroma_core.corosyncunknownpeersalert': {
            'Meta': {'object_name': 'CorosyncUnknownPeersAlert', 'db_table': "'chroma_core_alertstate'"},
            '_message': ('django.db.models.fields.TextField', [], {'null': 'True', 'db_column': "'message'"}),
            'active': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'alert_item_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'alert_item_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'alert_type': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'begin': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'dismissed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'end': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lustre_pid': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'record_type': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128'}),
            'severity': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'variant': ('django.db.models.fields.CharField', [], {'default': "'{}'", 'max_length': '512'})
        },
        'chroma_core.deployhostjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'DeployHostJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'managed_host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.detecttargetsjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'DetectTargetsJob'},
            'host_ids': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.enablelnetjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'EnableLNetJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'target_object': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.LNetConfiguration']"})
        },
        'chroma_core.failbacktargetjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'FailbackTargetJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedTarget']"})
        },
        'chroma_core.failovertargetjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'FailoverTargetJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedTarget']"})
        },
        'chroma_core.filesystemclientconfparam': {
            'Meta': {'ordering': "['id']", 'object_name': 'FilesystemClientConfParam', '_ormbases': ['chroma_core.ConfParam']},
            'confparam_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.ConfParam']", 'unique': 'True', 'primary_key': 'True'}),
            'filesystem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedFilesystem']"})
        },
        'chroma_core.filesystemglobalconfparam': {
            'Meta': {'ordering': "['id']", 'object_name': 'FilesystemGlobalConfParam', '_ormbases': ['chroma_core.ConfParam']},
            'confparam_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.ConfParam']", 'unique': 'True', 'primary_key': 'True'}),
            'filesystem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedFilesystem']"})
        },
        'chroma_core.forceremovecopytooljob': {
            'Meta': {'ordering': "['id']", 'object_name': 'ForceRemoveCopytoolJob'},
            'copytool': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.Copytool']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.forceremovehostjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'ForceRemoveHostJob'},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.forgetfilesystemjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'ForgetFilesystemJob'},
            'filesystem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedFilesystem']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.forgettargetjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'ForgetTargetJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedTarget']"})
        },
        'chroma_core.formattargetjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'FormatTargetJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedTarget']"})
        },
        'chroma_core.getcorosyncstatejob': {
            'Meta': {'ordering': "['id']", 'object_name': 'GetCorosyncStateJob', '_ormbases': ['chroma_core.Job']},
            'corosync_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.CorosyncConfiguration']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.getlnetstatejob': {
            'Meta': {'ordering': "['id']", 'object_name': 'GetLNetStateJob', '_ormbases': ['chroma_core.Job']},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.getpacemakerstatejob': {
            'Meta': {'ordering': "['id']", 'object_name': 'GetPacemakerStateJob', '_ormbases': ['chroma_core.Job']},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'pacemaker_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.PacemakerConfiguration']"})
        },
        'chroma_core.hostcontactalert': {
            'Meta': {'object_name': 'HostContactAlert', 'db_table': "'chroma_core_alertstate'"},
            '_message': ('django.db.models.fields.TextField', [], {'null': 'True', 'db_column': "'message'"}),
            'active': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'alert_item_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'alert_item_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'alert_type': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'begin': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'dismissed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'end': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lustre_pid': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'record_type': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128'}),
            'severity': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'variant': ('django.db.models.fields.CharField', [], {'default': "'{}'", 'max_length': '512'})
        },
        'chroma_core.hostofflinealert': {
            'Meta': {'object_name': 'HostOfflineAlert', 'db_table': "'chroma_core_alertstate'"},
            '_message': ('django.db.models.fields.TextField', [], {'null': 'True', 'db_column': "'message'"}),
            'active': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'alert_item_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'alert_item_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'alert_type': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'begin': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'dismissed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'end': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lustre_pid': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'record_type': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128'}),
            'severity': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'variant': ('django.db.models.fields.CharField', [], {'default': "'{}'", 'max_length': '512'})
        },
        'chroma_core.hostrebootevent': {
            'Meta': {'object_name': 'HostRebootEvent', 'db_table': "'chroma_core_alertstate'"},
            '_message': ('django.db.models.fields.TextField', [], {'null': 'True', 'db_column': "'message'"}),
            'active': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'alert_item_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'alert_item_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'alert_type': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'begin': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'dismissed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'end': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lustre_pid': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'record_type': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128'}),
            'severity': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'variant': ('django.db.models.fields.CharField', [], {'default': "'{}'", 'max_length': '512'})
        },
        'chroma_core.installhostpackagesjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'InstallHostPackagesJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'managed_host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.ipmibmcunavailablealert': {
            'Meta': {'object_name': 'IpmiBmcUnavailableAlert', 'db_table': "'chroma_core_alertstate'"},
            '_message': ('django.db.models.fields.TextField', [], {'null': 'True', 'db_column': "'message'"}),
            'active': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'alert_item_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'alert_item_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'alert_type': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'begin': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'dismissed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'end': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lustre_pid': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'record_type': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128'}),
            'severity': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'variant': ('django.db.models.fields.CharField', [], {'default': "'{}'", 'max_length': '512'})
        },
        'chroma_core.job': {
            'Meta': {'ordering': "['id']", 'object_name': 'Job'},
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
            'Meta': {'object_name': 'LearnEvent', 'db_table': "'chroma_core_alertstate'"},
            '_message': ('django.db.models.fields.TextField', [], {'null': 'True', 'db_column': "'message'"}),
            'active': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'alert_item_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'alert_item_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'alert_type': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'begin': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'dismissed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'end': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lustre_pid': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'record_type': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128'}),
            'severity': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'variant': ('django.db.models.fields.CharField', [], {'default': "'{}'", 'max_length': '512'})
        },
        'chroma_core.lnetconfiguration': {
            'Meta': {'ordering': "['id']", 'object_name': 'LNetConfiguration'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'host': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'lnet_configuration'", 'unique': 'True', 'to': "orm['chroma_core.ManagedHost']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'immutable_state': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'not_deleted': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'state_modified_at': ('django.db.models.fields.DateTimeField', [], {})
        },
        'chroma_core.lnetnidschangedalert': {
            'Meta': {'object_name': 'LNetNidsChangedAlert', 'db_table': "'chroma_core_alertstate'"},
            '_message': ('django.db.models.fields.TextField', [], {'null': 'True', 'db_column': "'message'"}),
            'active': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'alert_item_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'alert_item_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'alert_type': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'begin': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'dismissed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'end': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lustre_pid': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'record_type': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128'}),
            'severity': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'variant': ('django.db.models.fields.CharField', [], {'default': "'{}'", 'max_length': '512'})
        },
        'chroma_core.lnetofflinealert': {
            'Meta': {'object_name': 'LNetOfflineAlert', 'db_table': "'chroma_core_alertstate'"},
            '_message': ('django.db.models.fields.TextField', [], {'null': 'True', 'db_column': "'message'"}),
            'active': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'alert_item_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'alert_item_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'alert_type': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'begin': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'dismissed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'end': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lustre_pid': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'record_type': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128'}),
            'severity': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'variant': ('django.db.models.fields.CharField', [], {'default': "'{}'", 'max_length': '512'})
        },
        'chroma_core.loadlnetjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'LoadLNetJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'lnet_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.LNetConfiguration']"}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.logmessage': {
            'Meta': {'ordering': "['id']", 'object_name': 'LogMessage'},
            'datetime': ('django.db.models.fields.DateTimeField', [], {}),
            'facility': ('django.db.models.fields.SmallIntegerField', [], {}),
            'fqdn': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'message_class': ('django.db.models.fields.SmallIntegerField', [], {}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'severity': ('django.db.models.fields.SmallIntegerField', [], {}),
            'tag': ('django.db.models.fields.CharField', [], {'max_length': '63'})
        },
        'chroma_core.lustreclientmount': {
            'Meta': {'unique_together': "(('host', 'filesystem', 'not_deleted'),)", 'object_name': 'LustreClientMount'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'filesystem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedFilesystem']"}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'client_mounts'", 'to': "orm['chroma_core.ManagedHost']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'immutable_state': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'mountpoint': ('django.db.models.fields.CharField', [], {'max_length': '1024', 'null': 'True', 'blank': 'True'}),
            'not_deleted': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'state_modified_at': ('django.db.models.fields.DateTimeField', [], {})
        },
        'chroma_core.makeavailablefilesystemunavailable': {
            'Meta': {'ordering': "['id']", 'object_name': 'MakeAvailableFilesystemUnavailable'},
            'filesystem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedFilesystem']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.managedfilesystem': {
            'Meta': {'ordering': "['id']", 'unique_together': "(('name', 'mgs', 'not_deleted'),)", 'object_name': 'ManagedFilesystem'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'immutable_state': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'mdt_next_index': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'mgs': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedMgs']"}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '8'}),
            'not_deleted': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'ost_next_index': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'state_modified_at': ('django.db.models.fields.DateTimeField', [], {})
        },
        'chroma_core.managedhost': {
            'Meta': {'ordering': "['id']", 'unique_together': "(('address', 'not_deleted'),)", 'object_name': 'ManagedHost'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'boot_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'client_filesystems': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'workers'", 'symmetrical': 'False', 'through': "orm['chroma_core.LustreClientMount']", 'to': "orm['chroma_core.ManagedFilesystem']"}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'fqdn': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'ha_cluster_peers': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'ha_cluster_peers_rel_+'", 'null': 'True', 'to': "orm['chroma_core.ManagedHost']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'immutable_state': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'install_method': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'needs_update': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'nodename': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'not_deleted': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'properties': ('django.db.models.fields.TextField', [], {'default': "'{}'"}),
            'server_profile': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ServerProfile']", 'null': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'state_modified_at': ('django.db.models.fields.DateTimeField', [], {})
        },
        'chroma_core.managedmdt': {
            'Meta': {'ordering': "['id']", 'object_name': 'ManagedMdt', '_ormbases': ['chroma_core.ManagedTarget']},
            'filesystem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedFilesystem']"}),
            'index': ('django.db.models.fields.IntegerField', [], {}),
            'managedtarget_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.ManagedTarget']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.managedmgs': {
            'Meta': {'ordering': "['id']", 'object_name': 'ManagedMgs', '_ormbases': ['chroma_core.ManagedTarget']},
            'conf_param_version': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'conf_param_version_applied': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'managedtarget_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.ManagedTarget']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.managedost': {
            'Meta': {'ordering': "['id']", 'object_name': 'ManagedOst', '_ormbases': ['chroma_core.ManagedTarget']},
            'filesystem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedFilesystem']"}),
            'index': ('django.db.models.fields.IntegerField', [], {}),
            'managedtarget_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.ManagedTarget']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.managedtarget': {
            'Meta': {'ordering': "['id']", 'object_name': 'ManagedTarget'},
            'active_mount': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedTargetMount']", 'null': 'True', 'blank': 'True'}),
            'bytes_per_inode': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'ha_label': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'immutable_state': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'inode_count': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'inode_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'not_deleted': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'reformat': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'state_modified_at': ('django.db.models.fields.DateTimeField', [], {}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'volume': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.Volume']"})
        },
        'chroma_core.managedtargetmount': {
            'Meta': {'ordering': "['id']", 'object_name': 'ManagedTargetMount'},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'mount_point': ('django.db.models.fields.CharField', [], {'max_length': '512', 'null': 'True', 'blank': 'True'}),
            'not_deleted': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'primary': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedTarget']"}),
            'volume_node': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.VolumeNode']"})
        },
        'chroma_core.mdtconfparam': {
            'Meta': {'ordering': "['id']", 'object_name': 'MdtConfParam', '_ormbases': ['chroma_core.ConfParam']},
            'confparam_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.ConfParam']", 'unique': 'True', 'primary_key': 'True'}),
            'mdt': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedMdt']"})
        },
        'chroma_core.mountlustreclientjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'MountLustreClientJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'lustre_client_mount': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.LustreClientMount']"}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.mountlustrefilesystemsjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'MountLustreFilesystemsJob'},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.networkinterface': {
            'Meta': {'ordering': "['id']", 'unique_together': "(('host', 'name'),)", 'object_name': 'NetworkInterface'},
            'corosync_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.CorosyncConfiguration']", 'null': 'True'}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'inet4_address': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'inet4_prefix': ('django.db.models.fields.IntegerField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'state_up': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.nid': {
            'Meta': {'ordering': "['network_interface']", 'object_name': 'Nid'},
            'lnd_network': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'lnd_type': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True'}),
            'lnet_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.LNetConfiguration']"}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'network_interface': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.NetworkInterface']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.ntpconfiguration': {
            'Meta': {'ordering': "['id']", 'object_name': 'NTPConfiguration'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'host': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'_ntp_configuration'", 'unique': 'True', 'to': "orm['chroma_core.ManagedHost']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'immutable_state': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'not_deleted': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'state_modified_at': ('django.db.models.fields.DateTimeField', [], {})
        },
        'chroma_core.ostconfparam': {
            'Meta': {'ordering': "['id']", 'object_name': 'OstConfParam', '_ormbases': ['chroma_core.ConfParam']},
            'confparam_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.ConfParam']", 'unique': 'True', 'primary_key': 'True'}),
            'ost': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedOst']"})
        },
        'chroma_core.pacemakerconfiguration': {
            'Meta': {'ordering': "['id']", 'object_name': 'PacemakerConfiguration'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'host': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'_pacemaker_configuration'", 'unique': 'True', 'to': "orm['chroma_core.ManagedHost']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'immutable_state': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'not_deleted': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'state_modified_at': ('django.db.models.fields.DateTimeField', [], {})
        },
        'chroma_core.pacemakerstoppedalert': {
            'Meta': {'object_name': 'PacemakerStoppedAlert', 'db_table': "'chroma_core_alertstate'"},
            '_message': ('django.db.models.fields.TextField', [], {'null': 'True', 'db_column': "'message'"}),
            'active': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'alert_item_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'alert_item_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'alert_type': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'begin': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'dismissed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'end': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lustre_pid': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'record_type': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128'}),
            'severity': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'variant': ('django.db.models.fields.CharField', [], {'default': "'{}'", 'max_length': '512'})
        },
        'chroma_core.package': {
            'Meta': {'object_name': 'Package'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'})
        },
        'chroma_core.packageavailability': {
            'Meta': {'unique_together': "(('package_version', 'host'),)", 'object_name': 'PackageAvailability'},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'package_version': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.PackageVersion']"})
        },
        'chroma_core.packageinstallation': {
            'Meta': {'unique_together': "(('package_version', 'host'),)", 'object_name': 'PackageInstallation'},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'package_version': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.PackageVersion']"})
        },
        'chroma_core.packageversion': {
            'Meta': {'unique_together': "(('package', 'version', 'release'),)", 'object_name': 'PackageVersion'},
            'arch': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'epoch': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.Package']"}),
            'release': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        'chroma_core.powercontroldevice': {
            'Meta': {'unique_together': "(('address', 'port', 'not_deleted'),)", 'object_name': 'PowerControlDevice'},
            'address': ('django.db.models.fields.IPAddressField', [], {'max_length': '15'}),
            'device_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'instances'", 'to': "orm['chroma_core.PowerControlType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'not_deleted': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'options': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'port': ('django.db.models.fields.PositiveIntegerField', [], {'default': '23', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'})
        },
        'chroma_core.powercontroldeviceoutlet': {
            'Meta': {'unique_together': "(('device', 'identifier', 'not_deleted'),)", 'object_name': 'PowerControlDeviceOutlet'},
            'device': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'outlets'", 'to': "orm['chroma_core.PowerControlDevice']"}),
            'has_power': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'outlets'", 'null': 'True', 'to': "orm['chroma_core.ManagedHost']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'identifier': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'not_deleted': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'})
        },
        'chroma_core.powercontroldeviceunavailablealert': {
            'Meta': {'object_name': 'PowerControlDeviceUnavailableAlert', 'db_table': "'chroma_core_alertstate'"},
            '_message': ('django.db.models.fields.TextField', [], {'null': 'True', 'db_column': "'message'"}),
            'active': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'alert_item_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'alert_item_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'alert_type': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'begin': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'dismissed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'end': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lustre_pid': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'record_type': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128'}),
            'severity': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'variant': ('django.db.models.fields.CharField', [], {'default': "'{}'", 'max_length': '512'})
        },
        'chroma_core.powercontroltype': {
            'Meta': {'unique_together': "(('agent', 'make', 'model', 'not_deleted'),)", 'object_name': 'PowerControlType'},
            'agent': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'default_options': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'default_password': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'default_port': ('django.db.models.fields.PositiveIntegerField', [], {'default': '23', 'blank': 'True'}),
            'default_username': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'make': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'max_outlets': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0', 'blank': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'monitor_template': ('django.db.models.fields.CharField', [], {'default': "'%(agent)s %(options)s -a %(address)s -u %(port)s -l %(username)s -p %(password)s -o monitor'", 'max_length': '512', 'blank': 'True'}),
            'not_deleted': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'outlet_list_template': ('django.db.models.fields.CharField', [], {'default': "'%(agent)s %(options)s -a %(address)s -u %(port)s -l %(username)s -p %(password)s -o %(list_parameter)s'", 'max_length': '512', 'null': 'True', 'blank': 'True'}),
            'outlet_query_template': ('django.db.models.fields.CharField', [], {'default': "'%(agent)s %(options)s -a %(address)s -u %(port)s -l %(username)s -p %(password)s -o status -n %(identifier)s'", 'max_length': '512', 'blank': 'True'}),
            'powercycle_template': ('django.db.models.fields.CharField', [], {'default': "'%(agent)s %(options)s  -a %(address)s -u %(port)s -l %(username)s -p %(password)s -o reboot -n %(identifier)s'", 'max_length': '512', 'blank': 'True'}),
            'poweroff_template': ('django.db.models.fields.CharField', [], {'default': "'%(agent)s %(options)s -a %(address)s -u %(port)s -l %(username)s -p %(password)s -o off -n %(identifier)s'", 'max_length': '512', 'blank': 'True'}),
            'poweron_template': ('django.db.models.fields.CharField', [], {'default': "'%(agent)s %(options)s -a %(address)s -u %(port)s -l %(username)s -p %(password)s -o on -n %(identifier)s'", 'max_length': '512', 'blank': 'True'})
        },
        'chroma_core.powercyclehostjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'PowercycleHostJob'},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.poweroffhostjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'PoweroffHostJob'},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.poweronhostjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'PoweronHostJob'},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.reboothostjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'RebootHostJob'},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.registertargetjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'RegisterTargetJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedTarget']"})
        },
        'chroma_core.registrationtoken': {
            'Meta': {'object_name': 'RegistrationToken'},
            'cancelled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'credits': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'expiry': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'profile': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ServerProfile']", 'null': 'True'}),
            'secret': ('django.db.models.fields.CharField', [], {'default': "'B2B989BF495A2CDA446EDB14DC8C07FD'", 'max_length': '32'})
        },
        'chroma_core.removeconfiguredtargetjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'RemoveConfiguredTargetJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedTarget']"})
        },
        'chroma_core.removecopytooljob': {
            'Meta': {'ordering': "['id']", 'object_name': 'RemoveCopytoolJob'},
            'copytool': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.Copytool']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.removefilesystemjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'RemoveFilesystemJob'},
            'filesystem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedFilesystem']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.removehostjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'RemoveHostJob'},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.removelustreclientjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'RemoveLustreClientJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'lustre_client_mount': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.LustreClientMount']"}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.removemanagedhostjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'RemoveManagedHostJob'},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.removetargetjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'RemoveTargetJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedTarget']"})
        },
        'chroma_core.removeunconfiguredcopytooljob': {
            'Meta': {'ordering': "['id']", 'object_name': 'RemoveUnconfiguredCopytoolJob'},
            'copytool': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.Copytool']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.removeunconfiguredhostjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'RemoveUnconfiguredHostJob'},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.rsyslogconfiguration': {
            'Meta': {'ordering': "['id']", 'object_name': 'RSyslogConfiguration'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'host': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'_rsyslog_configuration'", 'unique': 'True', 'to': "orm['chroma_core.ManagedHost']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'immutable_state': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'not_deleted': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'state_modified_at': ('django.db.models.fields.DateTimeField', [], {})
        },
        'chroma_core.sample_10': {
            'Meta': {'unique_together': "(('id', 'dt'),)", 'object_name': 'Sample_10'},
            'dt': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'id': ('django.db.models.fields.IntegerField', [], {'primary_key': 'True'}),
            'len': ('django.db.models.fields.IntegerField', [], {}),
            'sum': ('django.db.models.fields.FloatField', [], {})
        },
        'chroma_core.sample_300': {
            'Meta': {'unique_together': "(('id', 'dt'),)", 'object_name': 'Sample_300'},
            'dt': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'id': ('django.db.models.fields.IntegerField', [], {'primary_key': 'True'}),
            'len': ('django.db.models.fields.IntegerField', [], {}),
            'sum': ('django.db.models.fields.FloatField', [], {})
        },
        'chroma_core.sample_3600': {
            'Meta': {'unique_together': "(('id', 'dt'),)", 'object_name': 'Sample_3600'},
            'dt': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'id': ('django.db.models.fields.IntegerField', [], {'primary_key': 'True'}),
            'len': ('django.db.models.fields.IntegerField', [], {}),
            'sum': ('django.db.models.fields.FloatField', [], {})
        },
        'chroma_core.sample_60': {
            'Meta': {'unique_together': "(('id', 'dt'),)", 'object_name': 'Sample_60'},
            'dt': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'id': ('django.db.models.fields.IntegerField', [], {'primary_key': 'True'}),
            'len': ('django.db.models.fields.IntegerField', [], {}),
            'sum': ('django.db.models.fields.FloatField', [], {})
        },
        'chroma_core.sample_86400': {
            'Meta': {'unique_together': "(('id', 'dt'),)", 'object_name': 'Sample_86400'},
            'dt': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'id': ('django.db.models.fields.IntegerField', [], {'primary_key': 'True'}),
            'len': ('django.db.models.fields.IntegerField', [], {}),
            'sum': ('django.db.models.fields.FloatField', [], {})
        },
        'chroma_core.series': {
            'Meta': {'unique_together': "(('content_type', 'object_id', 'name'),)", 'object_name': 'Series'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '30'})
        },
        'chroma_core.serverprofile': {
            'Meta': {'unique_together': "(('name',),)", 'object_name': 'ServerProfile'},
            'bundles': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['chroma_core.Bundle']", 'symmetrical': 'False'}),
            'corosync': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'corosync2': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'default': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'initial_state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'managed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'primary_key': 'True'}),
            'ntp': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'pacemaker': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'rsyslog': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'ui_description': ('django.db.models.fields.TextField', [], {}),
            'ui_name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'user_selectable': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'worker': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'chroma_core.serverprofilepackage': {
            'Meta': {'unique_together': "(('bundle', 'server_profile', 'package_name'),)", 'object_name': 'ServerProfilePackage'},
            'bundle': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.Bundle']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'package_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'server_profile': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ServerProfile']"})
        },
        'chroma_core.serverprofilevalidation': {
            'Meta': {'object_name': 'ServerProfileValidation'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'server_profile': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ServerProfile']"}),
            'test': ('django.db.models.fields.CharField', [], {'max_length': '256'})
        },
        'chroma_core.sethostprofilejob': {
            'Meta': {'ordering': "['id']", 'object_name': 'SetHostProfileJob', '_ormbases': ['chroma_core.Job']},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'server_profile': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ServerProfile']"})
        },
        'chroma_core.setuphostjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'SetupHostJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'target_object': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"})
        },
        'chroma_core.setupmonitoredhostjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'SetupMonitoredHostJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'target_object': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"})
        },
        'chroma_core.setupworkerjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'SetupWorkerJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'target_object': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"})
        },
        'chroma_core.shutdownhostjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'ShutdownHostJob'},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.simplehistostorebin': {
            'Meta': {'ordering': "['id']", 'object_name': 'SimpleHistoStoreBin'},
            'bin_idx': ('django.db.models.fields.IntegerField', [], {}),
            'histo_store_time': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.SimpleHistoStoreTime']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'value': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        'chroma_core.simplehistostoretime': {
            'Meta': {'ordering': "['id']", 'object_name': 'SimpleHistoStoreTime'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'storage_resource_statistic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.StorageResourceStatistic']"}),
            'time': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        'chroma_core.startcopytooljob': {
            'Meta': {'ordering': "['id']", 'object_name': 'StartCopytoolJob'},
            'copytool': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.Copytool']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.startcorosync2job': {
            'Meta': {'ordering': "['id']", 'object_name': 'StartCorosync2Job'},
            'corosync_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.Corosync2Configuration']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.startcorosyncjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'StartCorosyncJob'},
            'corosync_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.CorosyncConfiguration']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.startlnetjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'StartLNetJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'lnet_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.LNetConfiguration']"}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.startpacemakerjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'StartPacemakerJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'pacemaker_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.PacemakerConfiguration']"})
        },
        'chroma_core.startstoppedfilesystemjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'StartStoppedFilesystemJob'},
            'filesystem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedFilesystem']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.starttargetjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'StartTargetJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedTarget']"})
        },
        'chroma_core.startunavailablefilesystemjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'StartUnavailableFilesystemJob'},
            'filesystem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedFilesystem']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.stepresult': {
            'Meta': {'ordering': "['id']", 'object_name': 'StepResult'},
            'args': ('picklefield.fields.PickledObjectField', [], {}),
            'backtrace': ('django.db.models.fields.TextField', [], {}),
            'console': ('django.db.models.fields.TextField', [], {}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.Job']"}),
            'log': ('django.db.models.fields.TextField', [], {}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'result': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'default': "'incomplete'", 'max_length': '32'}),
            'step_count': ('django.db.models.fields.IntegerField', [], {}),
            'step_index': ('django.db.models.fields.IntegerField', [], {}),
            'step_klass': ('picklefield.fields.PickledObjectField', [], {})
        },
        'chroma_core.stonithnotenabledalert': {
            'Meta': {'object_name': 'StonithNotEnabledAlert', 'db_table': "'chroma_core_alertstate'"},
            '_message': ('django.db.models.fields.TextField', [], {'null': 'True', 'db_column': "'message'"}),
            'active': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'alert_item_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'alert_item_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'alert_type': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'begin': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'dismissed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'end': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lustre_pid': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'record_type': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128'}),
            'severity': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'variant': ('django.db.models.fields.CharField', [], {'default': "'{}'", 'max_length': '512'})
        },
        'chroma_core.stopcopytooljob': {
            'Meta': {'ordering': "['id']", 'object_name': 'StopCopytoolJob'},
            'copytool': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.Copytool']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.stopcorosync2job': {
            'Meta': {'ordering': "['id']", 'object_name': 'StopCorosync2Job'},
            'corosync_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.Corosync2Configuration']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.stopcorosyncjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'StopCorosyncJob'},
            'corosync_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.CorosyncConfiguration']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.stoplnetjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'StopLNetJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'lnet_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.LNetConfiguration']"}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.stoppacemakerjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'StopPacemakerJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'pacemaker_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.PacemakerConfiguration']"})
        },
        'chroma_core.stoptargetjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'StopTargetJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedTarget']"})
        },
        'chroma_core.stopunavailablefilesystemjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'StopUnavailableFilesystemJob'},
            'filesystem': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedFilesystem']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.storagealertpropagated': {
            'Meta': {'ordering': "['id']", 'unique_together': "(('storage_resource', 'alert_state'),)", 'object_name': 'StorageAlertPropagated'},
            'alert_state': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.StorageResourceAlert']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'storage_resource': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.StorageResourceRecord']"})
        },
        'chroma_core.storagepluginrecord': {
            'Meta': {'ordering': "['id']", 'unique_together': "(('module_name',),)", 'object_name': 'StoragePluginRecord'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'internal': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'module_name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        'chroma_core.storageresourcealert': {
            'Meta': {'object_name': 'StorageResourceAlert', 'db_table': "'chroma_core_alertstate'"},
            '_message': ('django.db.models.fields.TextField', [], {'null': 'True', 'db_column': "'message'"}),
            'active': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'alert_item_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'alert_item_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'alert_type': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'begin': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'dismissed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'end': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lustre_pid': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'record_type': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128'}),
            'severity': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'variant': ('django.db.models.fields.CharField', [], {'default': "'{}'", 'max_length': '512'})
        },
        'chroma_core.storageresourceattributereference': {
            'Meta': {'ordering': "['id']", 'object_name': 'StorageResourceAttributeReference'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'resource': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.StorageResourceRecord']"}),
            'value': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'value_resource'", 'null': 'True', 'on_delete': 'models.PROTECT', 'to': "orm['chroma_core.StorageResourceRecord']"})
        },
        'chroma_core.storageresourceattributeserialized': {
            'Meta': {'ordering': "['id']", 'object_name': 'StorageResourceAttributeSerialized'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'resource': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.StorageResourceRecord']"}),
            'value': ('django.db.models.fields.TextField', [], {})
        },
        'chroma_core.storageresourceclass': {
            'Meta': {'ordering': "['id']", 'unique_together': "(('storage_plugin', 'class_name'),)", 'object_name': 'StorageResourceClass'},
            'class_name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'storage_plugin': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.StoragePluginRecord']", 'on_delete': 'models.PROTECT'}),
            'user_creatable': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'chroma_core.storageresourceclassstatistic': {
            'Meta': {'ordering': "['id']", 'unique_together': "(('resource_class', 'name'),)", 'object_name': 'StorageResourceClassStatistic'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'resource_class': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.StorageResourceClass']"})
        },
        'chroma_core.storageresourcelearnevent': {
            'Meta': {'object_name': 'StorageResourceLearnEvent', 'db_table': "'chroma_core_alertstate'"},
            '_message': ('django.db.models.fields.TextField', [], {'null': 'True', 'db_column': "'message'"}),
            'active': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'alert_item_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'alert_item_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'alert_type': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'begin': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'dismissed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'end': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lustre_pid': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'record_type': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128'}),
            'severity': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'variant': ('django.db.models.fields.CharField', [], {'default': "'{}'", 'max_length': '512'})
        },
        'chroma_core.storageresourceoffline': {
            'Meta': {'object_name': 'StorageResourceOffline', 'db_table': "'chroma_core_alertstate'"},
            '_message': ('django.db.models.fields.TextField', [], {'null': 'True', 'db_column': "'message'"}),
            'active': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'alert_item_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'alert_item_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'alert_type': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'begin': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'dismissed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'end': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lustre_pid': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'record_type': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128'}),
            'severity': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'variant': ('django.db.models.fields.CharField', [], {'default': "'{}'", 'max_length': '512'})
        },
        'chroma_core.storageresourcerecord': {
            'Meta': {'ordering': "['id']", 'unique_together': "(('storage_id_str', 'storage_id_scope', 'resource_class'),)", 'object_name': 'StorageResourceRecord'},
            'alias': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'parents': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'resource_parent'", 'symmetrical': 'False', 'to': "orm['chroma_core.StorageResourceRecord']"}),
            'reported_by': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'resource_reported_by'", 'symmetrical': 'False', 'to': "orm['chroma_core.StorageResourceRecord']"}),
            'resource_class': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.StorageResourceClass']", 'on_delete': 'models.PROTECT'}),
            'storage_id_scope': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.StorageResourceRecord']", 'null': 'True', 'on_delete': 'models.PROTECT', 'blank': 'True'}),
            'storage_id_str': ('django.db.models.fields.CharField', [], {'max_length': '256'})
        },
        'chroma_core.storageresourcestatistic': {
            'Meta': {'ordering': "['id']", 'unique_together': "(('storage_resource', 'name'),)", 'object_name': 'StorageResourceStatistic'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'sample_period': ('django.db.models.fields.IntegerField', [], {}),
            'storage_resource': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.StorageResourceRecord']", 'on_delete': 'models.PROTECT'})
        },
        'chroma_core.syslogevent': {
            'Meta': {'object_name': 'SyslogEvent', 'db_table': "'chroma_core_alertstate'"},
            '_message': ('django.db.models.fields.TextField', [], {'null': 'True', 'db_column': "'message'"}),
            'active': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'alert_item_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'alert_item_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'alert_type': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'begin': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'dismissed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'end': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lustre_pid': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'record_type': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128'}),
            'severity': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'variant': ('django.db.models.fields.CharField', [], {'default': "'{}'", 'max_length': '512'})
        },
        'chroma_core.targetfailoveralert': {
            'Meta': {'object_name': 'TargetFailoverAlert', 'db_table': "'chroma_core_alertstate'"},
            '_message': ('django.db.models.fields.TextField', [], {'null': 'True', 'db_column': "'message'"}),
            'active': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'alert_item_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'alert_item_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'alert_type': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'begin': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'dismissed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'end': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lustre_pid': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'record_type': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128'}),
            'severity': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'variant': ('django.db.models.fields.CharField', [], {'default': "'{}'", 'max_length': '512'})
        },
        'chroma_core.targetofflinealert': {
            'Meta': {'object_name': 'TargetOfflineAlert', 'db_table': "'chroma_core_alertstate'"},
            '_message': ('django.db.models.fields.TextField', [], {'null': 'True', 'db_column': "'message'"}),
            'active': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'alert_item_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'alert_item_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'alert_type': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'begin': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'dismissed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'end': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lustre_pid': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'record_type': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128'}),
            'severity': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'variant': ('django.db.models.fields.CharField', [], {'default': "'{}'", 'max_length': '512'})
        },
        'chroma_core.targetrecoveryalert': {
            'Meta': {'object_name': 'TargetRecoveryAlert', 'db_table': "'chroma_core_alertstate'"},
            '_message': ('django.db.models.fields.TextField', [], {'null': 'True', 'db_column': "'message'"}),
            'active': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'alert_item_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'alert_item_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'alert_type': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'begin': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'dismissed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'end': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lustre_pid': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'record_type': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128'}),
            'severity': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'variant': ('django.db.models.fields.CharField', [], {'default': "'{}'", 'max_length': '512'})
        },
        'chroma_core.targetrecoveryinfo': {
            'Meta': {'ordering': "['id']", 'object_name': 'TargetRecoveryInfo'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'recovery_status': ('django.db.models.fields.TextField', [], {}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedTarget']"})
        },
        'chroma_core.testhostconnectionjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'TestHostConnectionJob', '_ormbases': ['chroma_core.Job']},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'credentials_key': ('django.db.models.fields.IntegerField', [], {}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.triggerpluginupdatesjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'TriggerPluginUpdatesJob'},
            'host_ids': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'plugin_names_json': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'chroma_core.unconfigurecorosync2job': {
            'Meta': {'ordering': "['id']", 'object_name': 'UnconfigureCorosync2Job'},
            'corosync_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.Corosync2Configuration']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.unconfigurecorosyncjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'UnconfigureCorosyncJob'},
            'corosync_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.CorosyncConfiguration']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.unconfigurelnetjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'UnconfigureLNetJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'target_object': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.LNetConfiguration']"})
        },
        'chroma_core.unconfigurentpjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'UnconfigureNTPJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'ntp_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.NTPConfiguration']"}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.unconfigurepacemakerjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'UnconfigurePacemakerJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'pacemaker_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.PacemakerConfiguration']"})
        },
        'chroma_core.unconfigurersyslogjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'UnconfigureRsyslogJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'rsyslog_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.RSyslogConfiguration']"})
        },
        'chroma_core.unloadlnetjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'UnloadLNetJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'lnet_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.LNetConfiguration']"}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.unmountlustreclientmountjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'UnmountLustreClientMountJob'},
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'}),
            'lustre_client_mount': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.LustreClientMount']"}),
            'old_state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'chroma_core.unmountlustrefilesystemsjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'UnmountLustreFilesystemsJob'},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.updatedevicesjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'UpdateDevicesJob'},
            'host_ids': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.updatejob': {
            'Meta': {'ordering': "['id']", 'object_name': 'UpdateJob', '_ormbases': ['chroma_core.Job']},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.updatenidsjob': {
            'Meta': {'ordering': "['id']", 'object_name': 'UpdateNidsJob'},
            'host_ids': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'job_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['chroma_core.Job']", 'unique': 'True', 'primary_key': 'True'})
        },
        'chroma_core.updatesavailablealert': {
            'Meta': {'object_name': 'UpdatesAvailableAlert', 'db_table': "'chroma_core_alertstate'"},
            '_message': ('django.db.models.fields.TextField', [], {'null': 'True', 'db_column': "'message'"}),
            'active': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'alert_item_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'alert_item_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'alert_type': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'begin': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'dismissed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'end': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lustre_pid': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'record_type': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128'}),
            'severity': ('django.db.models.fields.IntegerField', [], {'default': '20'}),
            'variant': ('django.db.models.fields.CharField', [], {'default': "'{}'", 'max_length': '512'})
        },
        'chroma_core.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            '_gui_config': ('django.db.models.fields.TextField', [], {'default': "'{}'", 'db_column': "'gui_config'"}),
            'accepted_eula': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'})
        },
        'chroma_core.volume': {
            'Meta': {'ordering': "['id']", 'unique_together': "(('storage_resource', 'not_deleted'),)", 'object_name': 'Volume'},
            'filesystem_type': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'not_deleted': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'size': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'storage_resource': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.StorageResourceRecord']", 'null': 'True', 'on_delete': 'models.PROTECT', 'blank': 'True'}),
            'usable_for_lustre': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        'chroma_core.volumenode': {
            'Meta': {'ordering': "['id']", 'unique_together': "(('host', 'path', 'not_deleted'),)", 'object_name': 'VolumeNode'},
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chroma_core.ManagedHost']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
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