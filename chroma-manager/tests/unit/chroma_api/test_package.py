from tests.unit.chroma_api.chroma_api_test_case import ChromaApiTestCase

from chroma_core.models.package import Package, PackageVersion, PackageInstallation, PackageAvailability
from tests.unit.chroma_core.helper import synthetic_host

from chroma_api.urls import api


class TestPackageResource(ChromaApiTestCase):
    def test_host_packages(self):
        """
        Test filtering packages by host
        """
        host1 = synthetic_host('host1')
        host2 = synthetic_host('host2')

        libacme = Package.objects.create(name='libacme')
        acme_utils = Package.objects.create(name='acme-utils')
        libacme_version = PackageVersion.objects.create(
            package=libacme, epoch=0, version='1.0', release='2', arch='x86_64')
        acme_utils_version = PackageVersion.objects.create(
            package=acme_utils, epoch=0, version='1.1', release='3', arch='x86_64')

        # on host1, libacme is installed and acme-utils is not installed but is available
        PackageInstallation.objects.create(package_version=libacme_version, host=host1)
        PackageAvailability.objects.create(package_version=acme_utils_version, host=host1)

        # on host2, libacme is installed
        PackageInstallation.objects.create(package_version=libacme_version, host=host2)

        # Query packages on host1
        response = self.api_client.get("/api/package/?host=%s" % host1.id)
        self.assertHttpOK(response)
        results = self.deserialize(response)['objects']
        self.assertEqual(len(results), 2)
        # Sort the result so we can check success deterministically
        results = sorted(results, lambda a, b: cmp(a['name'], b['name']))

        self.assertDictEqual(results[1], {
            'name': libacme.name,
            'epoch': libacme_version.epoch,
            'installed_hosts': [api.get_resource_uri(host1), api.get_resource_uri(host2)],
            'available_hosts': [],
            'version': libacme_version.version,
            'release': libacme_version.release,
            'arch': libacme_version.arch,
            'resource_uri': api.get_resource_uri(libacme_version)
        })
        self.assertDictEqual(results[0], {
            'name': acme_utils.name,
            'epoch': acme_utils_version.epoch,
            'installed_hosts': [],
            'available_hosts': [api.get_resource_uri(host1)],
            'version': acme_utils_version.version,
            'release': acme_utils_version.release,
            'arch': acme_utils_version.arch,
            'resource_uri': api.get_resource_uri(acme_utils_version)
        })

        # Query packages on host2
        response = self.api_client.get("/api/package/?host=%s" % host2.id)
        self.assertHttpOK(response)
        results = self.deserialize(response)['objects']
        self.assertEqual(len(results), 1)

        self.assertDictEqual(results[0], {
            'name': libacme.name,
            'epoch': libacme_version.epoch,
            'installed_hosts': [api.get_resource_uri(host1), api.get_resource_uri(host2)],
            'available_hosts': [],
            'version': libacme_version.version,
            'release': libacme_version.release,
            'arch': libacme_version.arch,
            'resource_uri': api.get_resource_uri(libacme_version)
        })
