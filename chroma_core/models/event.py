# Copyright (c) 2020 DDN. All rights reserved.
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
            lambda self_, value: self_.set_variant("learned_item_type", int, value),
            None,
        ),
    ]

    @property
    def learned_item(self):
        return self.__learned_item

    @learned_item.setter
    def learned_item(self, x):
        self.__learned_item = x

    __learned_item = VariantGenericForeignKey("learned_item_type", "learned_item_id")

    class Meta:
        app_label = "chroma_core"
        proxy = True

    @staticmethod
    def type_name():
        return "Autodetection"

    def alert_message(self):
        from chroma_core.models import ManagedTarget

        if isinstance(self.learned_item, ManagedTarget):
            return "Discovered formatted target %s" % self.learned_item
        else:
            return "Discovered %s" % self.learned_item


class AlertEvent(AlertStateBase):
    class Meta:
        app_label = "chroma_core"
        proxy = True

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
        proxy = True

    @staticmethod
    def type_name():
        return "Syslog"

    def alert_message(self):
        return self.message_str


class ClientConnectEvent(AlertStateBase):
    class Meta:
        app_label = "chroma_core"
        proxy = True

    variant_fields = [VariantDescriptor("message_str", str, None, None, "")]

    def alert_message(self):
        return self.message_str

    @staticmethod
    def type_name():
        return "ClientConnect"
