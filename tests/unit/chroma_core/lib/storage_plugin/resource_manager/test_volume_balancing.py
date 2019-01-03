from chroma_core.models.host import Volume, VolumeNode
from tests.unit.chroma_core.lib.storage_plugin.resource_manager.test_resource_manager import ResourceManagerTestCase


class TestVolumeBalancing(ResourceManagerTestCase):
    def test_volume_balance(self):
        hosts = []
        for i in range(0, 3):
            address = "host_%d" % i

            host = self._create_host(fqdn=address, nodename=address, address=address)

            resource_record, scannable_resource = self._make_global_resource(
                "linux", "PluginAgentResources", {"plugin_name": "linux", "host_id": host.id}
            )
            hosts.append({"host": host, "record": resource_record, "resource": scannable_resource})

            self.resource_manager.session_open(self.plugin, resource_record.pk, [scannable_resource], 60)

        for vol in range(0, 3):
            devices = ["serial_%s" % i for i in range(0, 3)]
            for host_info in hosts:
                resources = []
                for device in devices:
                    dev_resource = self._make_local_resource("linux", "ScsiDevice", serial=device, size=4096)
                    node_resource = self._make_local_resource(
                        "linux",
                        "LinuxDeviceNode",
                        path="/dev/%s" % device,
                        parents=[dev_resource],
                        host_id=host_info["host"].id,
                    )
                    resources.extend([dev_resource, node_resource])
                self.resource_manager.session_add_resources(host_info["record"].pk, resources)

        # Check that for 3 hosts, 3 volumes, they get one primary each
        expected = dict([(host_info["host"].address, 1) for host_info in hosts])
        actual = dict(
            [
                (host_info["host"].address, VolumeNode.objects.filter(host=host_info["host"], primary=True).count())
                for host_info in hosts
            ]
        )
        self.assertDictEqual(expected, actual)

    def test_consistent_order(self):
        """
        Test that the balancing algorithm respects FQDNs and volume labels in order to generate
        a predictable and pleasing assignment
        """

        hosts = []
        # NB deliberately shuffled indices to make sure the code is going to sort
        # back into right order and not depend on PK
        for i in [0, 1]:
            address = "host_%d" % i

            host = self._create_host(fqdn=address, nodename=address, address=address)

            resource_record, scannable_resource = self._make_global_resource(
                "linux", "PluginAgentResources", {"plugin_name": "linux", "host_id": host.id}
            )
            hosts.append({"host": host, "record": resource_record, "resource": scannable_resource})

            self.resource_manager.session_open(self.plugin, resource_record.pk, [scannable_resource], 60)

        # Balancing code refuses to assign secondaries unless some clustering information is known
        hosts[1]["host"].ha_cluster_peers.add(hosts[0]["host"])
        # hosts[1].save()
        hosts[0]["host"].ha_cluster_peers.add(hosts[1]["host"])
        # hosts[0].save()

        # NB deliberately shuffled indices to make sure the code is going to sort
        # back into right order and not depend on PK
        for vol in [1, 0, 2, 3]:
            devices = ["serial_%s" % i for i in range(0, 3)]
            for host_info in hosts:
                resources = []
                for device in devices:
                    dev_resource = self._make_local_resource("linux", "ScsiDevice", serial=device, size=4096)
                    node_resource = self._make_local_resource(
                        "linux",
                        "LinuxDeviceNode",
                        path="/dev/%s" % device,
                        parents=[dev_resource],
                        host_id=host_info["host"].id,
                    )
                    resources.extend([dev_resource, node_resource])
                self.resource_manager.session_add_resources(host_info["record"].pk, resources)

        expected = {"serial_0": ("host_0", "host_1")}

        for volume_label, (primary_fqdn, secondary_fqdn) in expected.items():
            volume = Volume.objects.get(label=volume_label)
            self.assertEqual(VolumeNode.objects.get(primary=True, volume=volume).host.fqdn, primary_fqdn)
            self.assertEqual(VolumeNode.objects.get(primary=False, use=True, volume=volume).host.fqdn, secondary_fqdn)
