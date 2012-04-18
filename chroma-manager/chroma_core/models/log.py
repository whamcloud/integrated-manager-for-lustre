#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from django.db import models

from chroma_core.models.utils import WorkaroundDateTimeField


class Systemevents(models.Model):
    """Django representation of record format emitted by MySQL"""
    id = models.AutoField(primary_key=True, db_column='ID')
    customerid = models.BigIntegerField(null=True, db_column='CustomerID',
                                        blank=True)
    receivedat = WorkaroundDateTimeField(null=True, db_column='ReceivedAt',
                                      blank=True)
    devicereportedtime = WorkaroundDateTimeField(null=True,
                                              db_column='DeviceReportedTime',
                                              blank=True)
    facility = models.IntegerField(null=True, db_column='Facility',
                                   blank=True)
    priority = models.IntegerField(null=True, db_column='Priority',
                                   blank=True)
    fromhost = models.CharField(max_length=60, db_column='FromHost',
                                blank=True)
    message = models.TextField(db_column='Message', blank=True)
    ntseverity = models.IntegerField(null=True, db_column='NTSeverity',
                                     blank=True)
    importance = models.IntegerField(null=True, db_column='Importance',
                                     blank=True)
    eventsource = models.CharField(max_length=60, db_column='EventSource',
                                   blank=True)
    eventuser = models.CharField(max_length=60, db_column='EventUser',
                                 blank=True)
    eventcategory = models.IntegerField(null=True, db_column='EventCategory',
                                        blank=True)
    eventid = models.IntegerField(null=True, db_column='EventID', blank=True)
    eventbinarydata = models.TextField(db_column='EventBinaryData',
                                       blank=True)
    maxavailable = models.IntegerField(null=True, db_column='MaxAvailable',
                                       blank=True)
    currusage = models.IntegerField(null=True, db_column='CurrUsage',
                                    blank=True)
    minusage = models.IntegerField(null=True, db_column='MinUsage', blank=True)
    maxusage = models.IntegerField(null=True, db_column='MaxUsage', blank=True)
    infounitid = models.IntegerField(null=True, db_column='InfoUnitID',
                                     blank=True)
    syslogtag = models.CharField(max_length=60, db_column='SysLogTag',
                                 blank=True)
    eventlogtype = models.CharField(max_length=60, db_column='EventLogType',
                                    blank=True)
    genericfilename = models.CharField(max_length=60,
                                       db_column='GenericFileName', blank=True)
    systemid = models.IntegerField(null=True, db_column='SystemID',
                                   blank=True)

    class Meta:
        db_table = u'SystemEvents'
        app_label = 'chroma_core'

    def get_message_class(self):
        if self.message.startswith(" LustreError:"):
            return "lustre_error"
        elif self.message.startswith(" Lustre:"):
            return "lustre"
        else:
            return "normal"


class LastSystemeventsProcessed(models.Model):
    """Record the ID of the latest log line that was
    already parsed for event generation"""
    class Meta:
        app_label = 'chroma_core'

    last = models.IntegerField(default = 0)
