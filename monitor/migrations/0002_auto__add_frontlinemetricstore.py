# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'FrontLineMetricStore'
        db.create_table('monitor_frontlinemetricstore', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'], null=True)),
            ('object_id', self.gf('django.db.models.fields.PositiveIntegerField')(null=True)),
            ('insert_time', self.gf('django.db.models.fields.DateTimeField')()),
            ('metric_name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('metric_type', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('value', self.gf('django.db.models.fields.FloatField')()),
        ))
        db.send_create_signal('monitor', ['FrontLineMetricStore'])

        # Change it to use the MEMORY engine
        db.execute('ALTER TABLE monitor_frontlinemetricstore ENGINE = MEMORY')

        # Add some sensible indexing to it
        db.execute('CREATE INDEX idx_fms_cot ON monitor_frontlinemetricstore (content_type_id, object_id, insert_time)')

        # FIXME? Drop django-created indexes for performance? Might have
        # unintended consequences.

    def backwards(self, orm):
        
        db.execute('DROP INDEX idx_fms_cot ON monitor_frontlinemetricstore')

        # Deleting model 'FrontLineMetricStore'
        db.delete_table('monitor_frontlinemetricstore')

    models = {
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
        'configure.managedhost': {
            'Meta': {'unique_together': "(('address', 'not_deleted'),)", 'object_name': 'ManagedHost'},
            'address': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'fqdn': ('django.db.models.fields.CharField', [], {'max_length': '255', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'not_deleted': ('django.db.models.fields.NullBooleanField', [], {'default': 'True', 'null': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '32'})
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
        'configure.storagepluginrecord': {
            'Meta': {'unique_together': "(('module_name',),)", 'object_name': 'StoragePluginRecord'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'module_name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        'configure.storageresourceclass': {
            'Meta': {'unique_together': "(('storage_plugin', 'class_name'),)", 'object_name': 'StorageResourceClass'},
            'class_name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'storage_plugin': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.StoragePluginRecord']"})
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
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'monitor.alertevent': {
            'Meta': {'object_name': 'AlertEvent', '_ormbases': ['monitor.Event']},
            'alert': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['monitor.AlertState']"}),
            'event_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['monitor.Event']", 'unique': 'True', 'primary_key': 'True'}),
            'message_str': ('django.db.models.fields.CharField', [], {'max_length': '512'})
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
        'monitor.clientconnectevent': {
            'Meta': {'object_name': 'ClientConnectEvent', '_ormbases': ['monitor.SyslogEvent']},
            'syslogevent_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['monitor.SyslogEvent']", 'unique': 'True', 'primary_key': 'True'})
        },
        'monitor.event': {
            'Meta': {'object_name': 'Event'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.ManagedHost']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'severity': ('django.db.models.fields.IntegerField', [], {})
        },
        'monitor.frontlinemetricstore': {
            'Meta': {'object_name': 'FrontLineMetricStore'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'insert_time': ('django.db.models.fields.DateTimeField', [], {}),
            'metric_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'metric_type': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'value': ('django.db.models.fields.FloatField', [], {})
        },
        'monitor.hostcontactalert': {
            'Meta': {'object_name': 'HostContactAlert', '_ormbases': ['monitor.AlertState']},
            'alertstate_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['monitor.AlertState']", 'unique': 'True', 'primary_key': 'True'})
        },
        'monitor.lastsystemeventsprocessed': {
            'Meta': {'object_name': 'LastSystemeventsProcessed'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'monitor.learnevent': {
            'Meta': {'object_name': 'LearnEvent', '_ormbases': ['monitor.Event']},
            'event_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['monitor.Event']", 'unique': 'True', 'primary_key': 'True'}),
            'learned_item_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'learned_item_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"})
        },
        'monitor.lnetofflinealert': {
            'Meta': {'object_name': 'LNetOfflineAlert', '_ormbases': ['monitor.AlertState']},
            'alertstate_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['monitor.AlertState']", 'unique': 'True', 'primary_key': 'True'})
        },
        'monitor.syslogevent': {
            'Meta': {'object_name': 'SyslogEvent', '_ormbases': ['monitor.Event']},
            'event_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['monitor.Event']", 'unique': 'True', 'primary_key': 'True'}),
            'lustre_pid': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'message_str': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'monitor.systemevents': {
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
        'monitor.targetfailoveralert': {
            'Meta': {'object_name': 'TargetFailoverAlert', '_ormbases': ['monitor.AlertState']},
            'alertstate_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['monitor.AlertState']", 'unique': 'True', 'primary_key': 'True'})
        },
        'monitor.targetofflinealert': {
            'Meta': {'object_name': 'TargetOfflineAlert', '_ormbases': ['monitor.AlertState']},
            'alertstate_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['monitor.AlertState']", 'unique': 'True', 'primary_key': 'True'})
        },
        'monitor.targetparam': {
            'Meta': {'object_name': 'TargetParam'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.ManagedTarget']"}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'monitor.targetrecoveryalert': {
            'Meta': {'object_name': 'TargetRecoveryAlert', '_ormbases': ['monitor.AlertState']},
            'alertstate_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['monitor.AlertState']", 'unique': 'True', 'primary_key': 'True'})
        },
        'monitor.targetrecoveryinfo': {
            'Meta': {'object_name': 'TargetRecoveryInfo'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'recovery_status': ('django.db.models.fields.TextField', [], {}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['configure.ManagedTarget']"})
        }
    }

    complete_apps = ['monitor']
