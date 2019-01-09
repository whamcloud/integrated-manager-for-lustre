import mock
from collections import defaultdict

from tests.unit.lib.iml_unit_test_case import IMLUnitTestCase

from django.db.models.signals import post_save, post_delete

from chroma_core.lib.long_polling import enable_long_polling


# Having imported we must immediately disconnect the receivers
post_save.disconnect(enable_long_polling.database_changed)
post_delete.disconnect(enable_long_polling.database_changed)


class TestEnableLongPolling(IMLUnitTestCase):
    def setUp(self):
        super(TestEnableLongPolling, self).setUp()

        self.mock_tables_changed = mock.Mock()
        mock.patch(
            "chroma_core.services.job_scheduler.job_scheduler_client.JobSchedulerClient", self.mock_tables_changed
        ).start()

        self.mock_propagate_table_change = mock.Mock()
        mock.patch(
            "chroma_core.lib.long_polling.enable_long_polling._propagate_table_change", self.mock_propagate_table_change
        ).start()

        self.is_managed = True
        self.mock_transaction = mock.MagicMock()
        self.mock_transaction.is_enabled = lambda using: self.is_managed
        mock.patch("chroma_core.lib.long_polling.enable_long_polling.transaction", self.mock_transaction).start()

        self.mock_sender = mock.MagicMock()
        self.mock_sender._meta = mock.MagicMock()

        self.test_chroma_table_names = [
            "chroma_core_leicester",
            "chroma_core_tottenham",
            "chroma_core_liverpool",
            "chroma_core_portsmouth",
        ]

        self.test_non_chroma_table_names = ["not_a_chroma_table"]
        self.test_table_names = self.test_chroma_table_names + self.test_non_chroma_table_names

        self.test_connection_names = ["ellen", "liz"]

        self.mock_sender._meta.db_table = self.test_chroma_table_names[0]

        def _commit_rollback():
            """Do it like this so each time a new instance is created"""
            commit_rollback = mock.MagicMock()
            commit_rollback.commit = lambda: 0
            commit_rollback.rollback = lambda: 0
            return commit_rollback

        enable_long_polling.transaction = mock.MagicMock()
        enable_long_polling.transaction.connections = defaultdict(lambda: _commit_rollback())
        self.is_managed = True
        enable_long_polling.transaction.is_managed = lambda using: self.is_managed

        self.addCleanup(mock.patch.stopall)

    def test_unmanaged_changes_propagate(self):
        """Unmanged changes should propagate immediately"""
        self.is_managed = False

        enable_long_polling.database_changed(self.mock_sender)

        self.mock_propagate_table_change.assert_called_once_with([self.mock_sender._meta.db_table])

    def test_managed_changes_batch(self):
        """Managed changes should propagate on commit"""
        original_transaction_commit = {}

        for test_connection_name in self.test_connection_names:
            original_transaction_commit[test_connection_name] = enable_long_polling.transaction.connections[
                test_connection_name
            ].commit

            for test_table_name in self.test_table_names:
                self.mock_sender._meta.db_table = test_table_name
                enable_long_polling.database_changed(self.mock_sender, using=test_connection_name)

            # Transaction.commit should now have changed.
            self.assertNotEqual(
                enable_long_polling.transaction.connections[test_connection_name].commit,
                original_transaction_commit[test_connection_name],
            )

            # We should not have propagated anything.
            self.assertEqual(self.mock_propagate_table_change.call_count, 0)

            # We should have 4 tables ready to be propagated
            self.assertEqual(
                len(enable_long_polling._pending_table_changes[test_connection_name]), len(self.test_chroma_table_names)
            )
            self.assertEqual(
                enable_long_polling._pending_table_changes[test_connection_name], set(self.test_chroma_table_names)
            )

        # Add again and nothing should change.
        for test_connection_name in self.test_connection_names:
            for test_table_name in self.test_table_names:
                self.mock_sender._meta.db_table = test_table_name
                enable_long_polling.database_changed(self.mock_sender, using=test_connection_name)

            # We should not have propagated anything.
            self.assertEqual(self.mock_propagate_table_change.call_count, 0)

            # We should have 4 tables ready to be propagated
            self.assertEqual(
                len(enable_long_polling._pending_table_changes[test_connection_name]), len(self.test_chroma_table_names)
            )
            self.assertEqual(
                enable_long_polling._pending_table_changes[test_connection_name], set(self.test_chroma_table_names)
            )

        for test_connection_name in self.test_connection_names:
            # Now call commit and things should happen.
            enable_long_polling.transaction.connections[test_connection_name].commit()

            # We should have no tables ready to be propagated
            self.assertTrue(test_connection_name not in enable_long_polling._pending_table_changes)

            # Transaction.commit should now be restored
            self.assertEqual(
                enable_long_polling.transaction.connections[test_connection_name].commit,
                original_transaction_commit[test_connection_name],
            )

            # We should have propagated the tables
            self.mock_propagate_table_change.assert_called_with(list(set(self.test_chroma_table_names)))

    def test_managed_changes_rollback(self):
        """Managed changes should not propagate on rollback"""
        original_transaction_rollback = {}

        for test_connection_name in self.test_connection_names:
            original_transaction_rollback[test_connection_name] = enable_long_polling.transaction.connections[
                test_connection_name
            ].rollback

            for test_table_name in self.test_table_names:
                self.mock_sender._meta.db_table = test_table_name
                enable_long_polling.database_changed(self.mock_sender, using=test_connection_name)

            # Transaction.rollback should now have changed.
            self.assertNotEqual(
                enable_long_polling.transaction.connections[test_connection_name].rollback,
                original_transaction_rollback[test_connection_name],
            )

            # We should not have propagated anything.
            self.assertEqual(self.mock_propagate_table_change.call_count, 0)

            # We should have 4 tables ready to be propagated
            self.assertEqual(
                len(enable_long_polling._pending_table_changes[test_connection_name]), len(self.test_chroma_table_names)
            )
            self.assertEqual(
                enable_long_polling._pending_table_changes[test_connection_name], set(self.test_chroma_table_names)
            )

        for test_connection_name in self.test_connection_names:
            # Now call rollback and things should happen.
            enable_long_polling.transaction.connections[test_connection_name].rollback()

            # We should have no tables ready to be propagated
            self.assertTrue(test_connection_name not in enable_long_polling._pending_table_changes)

            # Transaction.rollback should now be restored
            self.assertEqual(
                enable_long_polling.transaction.connections[test_connection_name].rollback,
                original_transaction_rollback[test_connection_name],
            )

        self.assertEqual(self.mock_propagate_table_change.call_count, 0)
