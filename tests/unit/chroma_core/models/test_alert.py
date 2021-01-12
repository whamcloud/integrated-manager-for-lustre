from tests.unit.lib.emf_unit_test_case import EMFUnitTestCase

from chroma_core.models import CommandRunningAlert
from chroma_core.models import CommandCancelledAlert
from chroma_core.models import AlertState


class TestAlert(EMFUnitTestCase):
    def test_message_regeneration_on_cast(self):
        command = self.make_command(message="Houston we have a problem")

        CommandRunningAlert.notify(command, True)

        alerts = AlertState.objects.all()
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].message(), "Command Houston we have a problem running")

        # Now cast it somewhere else.
        command_alert = alerts[0].cast(CommandCancelledAlert)

        self.assertEqual(command_alert.message(), "Command Houston we have a problem cancelled")

        # Ensure we still have only 1 alert.
        alerts = AlertState.objects.all()
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].message(), "Command Houston we have a problem cancelled")
