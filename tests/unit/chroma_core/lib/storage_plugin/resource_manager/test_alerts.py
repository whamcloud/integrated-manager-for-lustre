import logging

from tests.unit.chroma_core.lib.storage_plugin.resource_manager.test_resource_manager import ResourceManagerTestCase


class TestAlerts(ResourceManagerTestCase):
    def setUp(self):
        super(TestAlerts, self).setUp("alert_plugin")

    def _update_alerts(self, resource_manager, scannable_pk, resource, alert_klass):
        result = []
        for ac in resource._meta.alert_conditions:
            if isinstance(ac, alert_klass):
                alert_list = ac.test(resource)

                for name, attribute, active, severity in alert_list:
                    resource_manager.session_notify_alert(
                        scannable_pk, resource._handle, active, severity, name, attribute
                    )
                    result.append((name, attribute, active))

        return result

    def _update_alerts_anytrue(self, resource_manager, *args, **kwargs):
        alerts = self._update_alerts(resource_manager, *args, **kwargs)
        for alert in alerts:
            if alert[2]:
                return True
        return False

    def test_multiple_alerts(self):
        """Test multiple AlertConditions acting on the same attribute"""
        resource_record, controller_resource = self._make_global_resource(
            "alert_plugin", "Controller", {"address": "foo", "temperature": 40, "status": "OK", "multi_status": "OK"}
        )
        lun_resource = self._make_local_resource(
            "alert_plugin", "Lun", lun_id="foo", size=1024 * 1024 * 650, parents=[controller_resource]
        )

        # Open session
        self.resource_manager.session_open(self.plugin, resource_record.pk, [controller_resource, lun_resource], 60)

        from chroma_core.lib.storage_plugin.api.alert_conditions import ValueCondition

        # Go into failed state and send notification
        controller_resource.multi_status = "FAIL1"
        alerts = self._update_alerts(self.resource_manager, resource_record.pk, controller_resource, ValueCondition)
        n = 0
        for alert in alerts:
            if alert[2]:
                n += 1

        self.assertEqual(n, 2, alerts)

        # Check that the alert is now set on couplet
        from chroma_core.models import StorageResourceAlert

        self.assertEqual(StorageResourceAlert.objects.filter(active=True).count(), 2)

    def test_raise_alert(self):
        resource_record, controller_resource = self._make_global_resource(
            "alert_plugin", "Controller", {"address": "foo", "temperature": 40, "status": "OK", "multi_status": "OK"}
        )
        lun_resource = self._make_local_resource(
            "alert_plugin", "Lun", lun_id="foo", size=1024 * 1024 * 650, parents=[controller_resource]
        )

        # Open session
        self.resource_manager.session_open(self.plugin, resource_record.pk, [controller_resource, lun_resource], 60)

        from chroma_core.lib.storage_plugin.api.alert_conditions import ValueCondition

        # Go into failed state and send notification
        controller_resource.status = "FAILED"
        self.assertEqual(
            True,
            self._update_alerts_anytrue(self.resource_manager, resource_record.pk, controller_resource, ValueCondition),
        )

        from chroma_core.models import StorageResourceAlert, StorageAlertPropagated

        # Check that the alert is now set on couplet
        self.assertEqual(StorageResourceAlert.objects.filter(active=True).count(), 1)
        self.assertEqual(StorageResourceAlert.objects.get().severity, logging.WARNING)

        # FIXME: make this string more sensible
        self.assertEqual(StorageResourceAlert.objects.get().message(), "Controller failure (Controller Controller foo)")

        # Check that the alert is now set on controller (propagation)
        self.assertEqual(StorageAlertPropagated.objects.filter().count(), 1)

        # Leave failed state and send notification
        controller_resource.status = "OK"
        self.assertEqual(
            False,
            self._update_alerts_anytrue(self.resource_manager, resource_record.pk, controller_resource, ValueCondition),
        )

        # Check that the alert is now unset on couplet
        self.assertEqual(StorageResourceAlert.objects.filter(active=True).count(), 0)
        # Check that the alert is now unset on controller (propagation)
        self.assertEqual(StorageAlertPropagated.objects.filter().count(), 0)

        # Now try setting something which should have a different severity (respect difference betwee
        # warn_states and error_states on AlertCondition)
        controller_resource.status = "BADLY_FAILED"
        self.assertEqual(
            True,
            self._update_alerts_anytrue(self.resource_manager, resource_record.pk, controller_resource, ValueCondition),
        )
        self.assertEqual(StorageResourceAlert.objects.filter(active=True).count(), 1)
        self.assertEqual(StorageResourceAlert.objects.get(active=True).severity, logging.ERROR)

    def test_alert_deletion(self):
        resource_record, controller_resource = self._make_global_resource(
            "alert_plugin", "Controller", {"address": "foo", "temperature": 40, "status": "OK", "multi_status": "OK"}
        )
        lun_resource = self._make_local_resource(
            "alert_plugin", "Lun", lun_id="foo", size=1024 * 1024 * 650, parents=[controller_resource]
        )

        # Open session
        self.resource_manager.session_open(self.plugin, resource_record.pk, [controller_resource, lun_resource], 60)

        from chroma_core.lib.storage_plugin.api.alert_conditions import ValueCondition

        # Go into failed state and send notification
        controller_resource.status = "FAILED"
        self.assertEqual(
            True,
            self._update_alerts_anytrue(self.resource_manager, resource_record.pk, controller_resource, ValueCondition),
        )

        from chroma_core.models import StorageResourceAlert, StorageAlertPropagated

        # Check that the alert is now set on couplet
        self.assertEqual(StorageResourceAlert.objects.filter(active=None).count(), 0)
        self.assertEqual(StorageResourceAlert.objects.filter(active=True).count(), 1)
        # Check that the alert is now set on controller (propagation)
        self.assertEqual(StorageAlertPropagated.objects.filter().count(), 1)

        alert_message_before_delete = StorageResourceAlert.objects.filter(active=True)[0].message()

        self.resource_manager.global_remove_resource(resource_record.pk)

        self.assertEqual(alert_message_before_delete, StorageResourceAlert.objects.filter(active=None)[0].message())

        # Check that the alert is now unset on couplet
        self.assertEqual(StorageResourceAlert.objects.filter(active=None).count(), 1)
        self.assertEqual(StorageResourceAlert.objects.filter(active=True).count(), 0)
        # Check that the alert is now unset on controller (propagation)
        self.assertEqual(StorageAlertPropagated.objects.filter().count(), 0)

    def test_bound_alert(self):
        resource_record, controller_resource = self._make_global_resource(
            "alert_plugin", "Controller", {"address": "foo", "temperature": 40, "status": "OK", "multi_status": "OK"}
        )
        lun_resource = self._make_local_resource(
            "alert_plugin", "Lun", lun_id="foo", size=1024 * 1024 * 650, parents=[controller_resource]
        )

        from chroma_core.lib.storage_plugin.api.alert_conditions import UpperBoundCondition, LowerBoundCondition

        # Open session
        self.resource_manager.session_open(self.plugin, resource_record.pk, [controller_resource, lun_resource], 60)

        controller_resource.temperature = 86
        self.assertEqual(
            True,
            self._update_alerts_anytrue(
                self.resource_manager, resource_record.pk, controller_resource, UpperBoundCondition
            ),
        )

        controller_resource.temperature = 84
        self.assertEqual(
            False,
            self._update_alerts_anytrue(
                self.resource_manager, resource_record.pk, controller_resource, UpperBoundCondition
            ),
        )

        controller_resource.temperature = -1
        self.assertEqual(
            True,
            self._update_alerts_anytrue(
                self.resource_manager, resource_record.pk, controller_resource, LowerBoundCondition
            ),
        )

        controller_resource.temperature = 1
        self.assertEqual(
            False,
            self._update_alerts_anytrue(
                self.resource_manager, resource_record.pk, controller_resource, LowerBoundCondition
            ),
        )
