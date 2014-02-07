import glob
import json
from django.test import TestCase
import mock
import os
from chroma_core.models.filesystem import ManagedFilesystem
from chroma_core.models.host import Nid
from chroma_core.models.host import ManagedHost, Volume, VolumeNode, DetectTargetsJob
from chroma_core.models.target import ManagedOst, ManagedTargetMount, ManagedTarget
from tests.unit.chroma_core.helper import synthetic_host, synchronous_run_job, load_default_profile


class TestDetection(TestCase):
    mock_servers = {}

    def setUp(self):
        load_default_profile()

    def test_combined_mgs_mdt(self):
        def fixture_glob(g):
            return glob.glob(os.path.join(os.path.dirname(__file__), "fixtures/test_combined_mgs_mdt", g))

        for path in fixture_glob("*_nid.txt"):
            address = os.path.basename(path).split("_")[0]
            nids = [Nid.split_nid_string(l.strip()) for l in open(path).readlines()]
            synthetic_host(address, nids)

        host_data = {}
        for path in fixture_glob("*detect_scan_output.txt"):
            address = os.path.basename(path).split("_")[0]
            data = json.load(open(path))['result']
            host_data[ManagedHost.objects.get(address = address)] = data

        # Simplified volume construction:
        #  * Assume all device paths referenced in detection exist
        #  * Assume all devices visible on all hosts
        #  * Assume device node paths are identical on all hosts
        devpaths = set()
        for host, data in host_data.items():
            for lt in data['local_targets']:
                for d in lt['devices']:
                    if not d in devpaths:
                        devpaths.add(d)
                        volume = Volume.objects.create()
                        for host in host_data.keys():
                            VolumeNode.objects.create(volume = volume, path = d, host = host)

        def _detect_scan(host, command, args = None):
            self.assertEqual(command, 'detect_scan')
            return host_data[host]

        job = DetectTargetsJob.objects.create()

        with mock.patch("chroma_core.lib.job.Step.invoke_agent", new = mock.Mock(side_effect = _detect_scan)):
            synchronous_run_job(job)

        self.assertEqual(ManagedFilesystem.objects.count(), 1)
        self.assertEqual(ManagedFilesystem.objects.get().name, "test18fs")

        self.assertEqual(ManagedOst.objects.count(), 8)

        for t in ManagedTarget.objects.all():
            self.assertEqual(t.immutable_state, True)

        def assertMount(target_name, primary_host, failover_hosts = list()):
            target = ManagedTarget.objects.get(name = target_name)
            self.assertEquals(ManagedTargetMount.objects.filter(target = target).count(), 1 + len(failover_hosts))
            self.assertEquals(ManagedTargetMount.objects.filter(target = target, primary = True, host = ManagedHost.objects.get(address = primary_host)).count(), 1)
            for h in failover_hosts:
                self.assertEquals(ManagedTargetMount.objects.filter(target = target, primary = False, host = ManagedHost.objects.get(address = h)).count(), 1)

        assertMount('MGS', 'kp-lustre-1-8-mgs-1')
        assertMount('test18fs-MDT0000', 'kp-lustre-1-8-mgs-1')
        assertMount('test18fs-OST0000', 'kp-lustre-1-8-oss-1')
        assertMount('test18fs-OST0001', 'kp-lustre-1-8-oss-1')
        assertMount('test18fs-OST0002', 'kp-lustre-1-8-oss-2')
        assertMount('test18fs-OST0003', 'kp-lustre-1-8-oss-2')
        assertMount('test18fs-OST0004', 'kp-lustre-1-8-oss-3')
        assertMount('test18fs-OST0005', 'kp-lustre-1-8-oss-3')
        assertMount('test18fs-OST0006', 'kp-lustre-1-8-oss-4')
        assertMount('test18fs-OST0007', 'kp-lustre-1-8-oss-4')

        self.assertEqual(ManagedFilesystem.objects.get().state, 'available')
