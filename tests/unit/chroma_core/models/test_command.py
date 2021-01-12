from django.contrib.contenttypes.models import ContentType

from tests.unit.lib.emf_unit_test_case import EMFUnitTestCase
from chroma_core.models import CommandRunningAlert
from chroma_core.models import CommandCancelledAlert
from chroma_core.models import CommandErroredAlert
from chroma_core.models import CommandSuccessfulAlert
from chroma_core.models import AlertState


class TestCommand(EMFUnitTestCase):
    def test_command_handles_alert(self):
        """Check that Commands create and delete alerts"""

        for cancelled in [False, True]:
            for errored in [False, True]:
                command = self.make_command(complete=False, message="test %s:%s" % (cancelled, errored))

                self.assertEqual(command.complete, False)
                self.assertEqual(command.message, "test %s:%s" % (cancelled, errored))
                self.assertEqual(len(CommandRunningAlert.objects.filter(alert_item_id=command.id, active=False)), 0)
                self.assertEqual(len(CommandRunningAlert.objects.filter(alert_item_id=command.id, active=True)), 1)

                command.completed(errored, cancelled)

                self.assertEqual(command.complete, True)
                self.assertEqual(command.errored, errored)
                self.assertEqual(command.cancelled, cancelled)

                if command.errored:
                    expected_alert_class = CommandErroredAlert
                elif command.cancelled:
                    expected_alert_class = CommandCancelledAlert
                else:
                    expected_alert_class = CommandSuccessfulAlert

                self.assertEqual(len(expected_alert_class.objects.filter(alert_item_id=command.id, active=True)), 0)

                self.assertEqual(len(expected_alert_class.objects.filter(alert_item_id=command.id, active=None)), 1)

                command_alerts = AlertState.objects.filter(
                    alert_item_id=command.id, alert_item_type=ContentType.objects.get_for_model(command)
                )

                # We should 1 CommandAlert for that command.
                self.assertEqual(
                    len(
                        [
                            command_alert
                            for command_alert in command_alerts
                            if type(command_alert) in command.command_alert_types
                        ]
                    ),
                    1,
                )
