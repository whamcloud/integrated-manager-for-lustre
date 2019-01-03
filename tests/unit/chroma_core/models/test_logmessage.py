from tests.unit.lib.iml_unit_test_case import IMLUnitTestCase
from chroma_core.models import LogMessage, MessageClass


class TestLogMessage(IMLUnitTestCase):
    def test_classification(self):
        """
        Test the classification code correctly classfies messages.
        """

        test_messages = {
            "Lustre: Lustre output here": MessageClass.LUSTRE,
            "LustreError: Lustre output here": MessageClass.LUSTRE_ERROR,
            "[NOT A TIME STAMP ] Lustre: Lustre output here": MessageClass.NORMAL,
            "[1234567A89] LustreError: Not A Time Stamp": MessageClass.NORMAL,
            "[123456789.123456789A] LustreError: Not A Time Stamp": MessageClass.NORMAL,
            "Nothing to see here": MessageClass.NORMAL,
        }

        for with_timestamp in [False, True]:
            for test_message, message_class in test_messages.iteritems():
                test_message = ("[9830337.7944560] " if with_timestamp else "") + test_message

                self.assertEqual(LogMessage.get_message_class(test_message), message_class, test_message)
