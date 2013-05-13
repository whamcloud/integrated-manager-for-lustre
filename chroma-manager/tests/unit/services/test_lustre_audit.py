import datetime
from chroma_core.services.job_scheduler.job_scheduler_client import JobSchedulerClient
from django.test import TestCase
import mock
from tests.unit.chroma_core.helper import synthetic_host, load_default_profile

from chroma_core.models import Package, PackageVersion, PackageAvailability
from chroma_core.services.lustre_audit import UpdateScan
from chroma_core.models.package import PackageInstallation


class TestPackageAudit(TestCase):
    def setUp(self):
        load_default_profile()
        self.old_notify = JobSchedulerClient.notify
        JobSchedulerClient.notify = mock.Mock()

    def tearDown(self):
        JobSchedulerClient.notify = self.old_notify

    def _send_package_data(self, host, data):
        # UpdateScan is a weird class, we have to instantiate and assign a host
        # to run the function we're testing.
        self.update_scan = UpdateScan()
        self.update_scan.host = host
        self.update_scan.started_at = datetime.datetime.utcnow()
        self.update_scan.update_packages(data)

    def test_update_notification(self):
        """
        A host sends its initial report, containing some information about what packages
        are installed.  Test that this results in appropriate database records for the packages.
        """

        host = synthetic_host('test1')

        self._send_package_data(host, {
            'bundle1': {
                'libacme': {
                    'installed': [('0', '1.0', '2', 'x86_64')],
                    'available': [('0', '1.0', '3', 'x86_64')]
                }
            }
        })
        # We reported different installed vs. available versions -- a notification that updates
        # are needed should have been emitted
        JobSchedulerClient.notify.assert_called_once_with(host, self.update_scan.started_at, {'needs_update': True})

    def test_version_recording(self):
        """
        Test that the package database models are updated to reflect reports
        from hosts, and that when hosts no longer report a package its record
        is removed.

        Note that this exercises a number of states in sequence in order to test
        not just that each state is correctly handled from cold, but that each
        state is handlded as a transition from the previous one.
        """

        host = synthetic_host('test1')

        # In a quiet state, same version available as installed
        # =====================================================
        self._send_package_data(host, {
            'bundle1': {
                'libacme': {
                    'installed': [('0', '1.0', '2', 'x86_64')],
                    'available': [('0', '1.0', '2', 'x86_64')]
                }
            }
        })

        # The one package should have been recorded
        package = Package.objects.get()
        self.assertEqual(package.name, 'libacme')

        package_version = PackageVersion.objects.get()
        self.assertEqual(package_version.epoch, 0)
        self.assertEqual(package_version.version, '1.0')
        self.assertEqual(package_version.release, '2')

        package_installed = PackageInstallation.objects.get()
        self.assertEqual(package_installed.host, host)
        self.assertEqual(package_installed.package_version, package_version)

        package_available = PackageAvailability.objects.get()
        self.assertEqual(package_available.host, host)
        self.assertEqual(package_available.package_version, package_version)

        # In a state waiting for an upgrade
        # =================================
        self._send_package_data(host, {
            'bundle1': {
                'libacme': {
                    'installed': [('0', '1.0', '2', 'x86_64')],
                    'available': [('0', '1.0', '3', 'x86_64')]
                }
            }
        })

        # Should still be just one Package
        package = Package.objects.get()
        self.assertEqual(package.name, 'libacme')

        # ... but now two PackageVersions
        package_version_old = PackageVersion.objects.get(release='2')
        self.assertEqual(package_version.epoch, 0)
        self.assertEqual(package_version.version, '1.0')

        package_version_new = PackageVersion.objects.get(release='3')
        self.assertEqual(package_version.epoch, 0)
        self.assertEqual(package_version.version, '1.0')

        # ... one of which is installed
        package_installed = PackageInstallation.objects.get()
        self.assertEqual(package_installed.host, host)
        self.assertEqual(package_installed.package_version, package_version_old)

        # ... the other of which is available
        package_available = PackageAvailability.objects.get()
        self.assertEqual(package_available.host, host)
        self.assertEqual(package_available.package_version, package_version_new)

        # In an upgraded state
        # ====================

        self._send_package_data(host, {
            'bundle1': {
                'libacme': {
                    'installed': [('0', '1.0', '3', 'x86_64')],
                    'available': [('0', '1.0', '3', 'x86_64')]
                }
            }
        })

        # We should be back to having just a single Package, PackageVersion, PackageInstallation and PackageAvailability
        package = Package.objects.get()
        self.assertEqual(package.name, 'libacme')

        package_version = PackageVersion.objects.get()
        self.assertEqual(package_version.epoch, 0)
        self.assertEqual(package_version.version, '1.0')
        self.assertEqual(package_version.release, '3')

        package_installed = PackageInstallation.objects.get()
        self.assertEqual(package_installed.host, host)
        self.assertEqual(package_installed.package_version, package_version)

        package_available = PackageAvailability.objects.get()
        self.assertEqual(package_available.host, host)
        self.assertEqual(package_available.package_version, package_version)

        # When the package is neither available nor installed
        # ===================================================

        self._send_package_data(host, {
            'bundle1': {}
        })

        # The package should be gone
        self.assertFalse(PackageAvailability.objects.exists())
        self.assertFalse(PackageInstallation.objects.exists())
        self.assertFalse(PackageVersion.objects.exists())
        self.assertFalse(Package.objects.exists())
