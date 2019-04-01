import mock

from django.test import TestCase

from chroma_core.models import Command
from chroma_core.services.log import log_register

log = log_register("iml_test_case")


class IMLUnitTestCase(TestCase):
    def setUp(self):
        super(IMLUnitTestCase, self).setUp()

        mock.patch("chroma_core.services.job_scheduler.job_scheduler.LockQueue.put").start()
        mock.patch("chroma_core.services.dbutils.exit_if_in_transaction").start()

    def make_command(self, complete=False, created_at=None, errored=True, message="test"):

        """

        :param complete: Bool True when the command has completed
        :param created_at: DateTime of the creation time
        :param errored: Bool True if the command errored
        :param message: str Message associated with the command
        :return: Command The command created.
        """
        command = Command.objects.create(message=message, complete=complete, errored=errored)

        #  Command.created_at is auto_add_now - so have to update it
        if created_at is not None:
            command.created_at = created_at
            command.save()

        return command
