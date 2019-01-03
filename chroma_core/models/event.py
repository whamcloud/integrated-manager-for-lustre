# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from chroma_core.models.alert import AlertStateBase, AlertState
from chroma_core.models.sparse_model import VariantGenericForeignKey, VariantDescriptor


class LearnEvent(AlertStateBase):
    variant_fields = [
        VariantDescriptor("learned_item_id", int, None, None, 0),
        VariantDescriptor(
            "learned_item_type",
            int,
            None,
            lambda self_, value: self_.set_variant("learned_item_type", int, value.id),
            None,
        ),
    ]

    learned_item = VariantGenericForeignKey("learned_item_type", "learned_item_id")

    class Meta:
        app_label = "chroma_core"
        db_table = AlertStateBase.table_name

    @staticmethod
    def type_name():
        return "Autodetection"

    def alert_message(self):
        from chroma_core.models import ManagedTarget, ManagedFilesystem, ManagedTargetMount

        if isinstance(self.learned_item, ManagedTargetMount):
            return "Discovered mount point of %s on %s" % (self.learned_item, self.learned_item.host)
        elif isinstance(self.learned_item, ManagedTarget):
            return "Discovered formatted target %s" % self.learned_item
        elif isinstance(self.learned_item, ManagedFilesystem):
            return "Discovered filesystem %s on MGS %s" % (self.learned_item, self.learned_item.mgs.primary_host)
        else:
            return "Discovered %s" % self.learned_item


class AlertEvent(AlertStateBase):
    class Meta:
        app_label = "chroma_core"
        db_table = AlertStateBase.table_name

    variant_fields = [
        VariantDescriptor("message_str", str, None, None, ""),
        VariantDescriptor(
            "alert",
            AlertState,
            lambda self_: AlertState.objects.get(id=self_.get_variant("alert_id", None, int)),
            lambda self_, value: self_.set_variant("alert_id", int, value.id),
            None,
        ),
    ]

    @staticmethod
    def type_name():
        return "Alert"

    def alert_message(self):
        return self.message_str


class SyslogEvent(AlertStateBase):
    variant_fields = [VariantDescriptor("message_str", str, None, None, "")]

    class Meta:
        app_label = "chroma_core"
        db_table = AlertStateBase.table_name

    @staticmethod
    def type_name():
        return "Syslog"

    def alert_message(self):
        return self.message_str


class ClientConnectEvent(AlertStateBase):
    class Meta:
        app_label = "chroma_core"
        db_table = AlertStateBase.table_name

    variant_fields = [VariantDescriptor("message_str", str, None, None, "")]

    def alert_message(self):
        return self.message_str

    @staticmethod
    def type_name():
        return "ClientConnect"
