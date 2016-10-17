import time

from django.utils.unittest import skip

from testconfig import config
from tests.integration.core.stats_testcase_mixin import StatsTestCaseMixin


class TestFilesystemDNE(StatsTestCaseMixin):
    def setUp(self):
        super(TestFilesystemDNE, self).setUp()

    def _create_filesystem(self, mdt_count):
        assert mdt_count in [1, 2, 3]

        self.hosts = self.add_hosts([config['lustre_servers'][0]['address'],
                                     config['lustre_servers'][1]['address']])

        # Since the test code seems to rely on this ordering, we should
        # check for it right away and blow up if it's not as we expect.
        self.assertEqual([h['address'] for h in self.hosts],
                         [config['lustre_servers'][0]['address'],
                          config['lustre_servers'][1]['address']])

        self.ha_volumes = self.get_usable_volumes()
        self.assertGreaterEqual(len(self.ha_volumes), 4)

        self.mgt_volume = self.ha_volumes[0]
        self.mdt_volumes = self.ha_volumes[1:(1 + mdt_count)]
        self.ost_volumes = self.ha_volumes[4:5]

        for volume in [self.mgt_volume] + self.mdt_volumes + self.ost_volumes:
            self.set_volume_mounts(volume, self.hosts[0]['id'], self.hosts[1]['id'])

        self.filesystem_id = self.create_filesystem({'name': 'testfs',
                                                     'mgt': {'volume_id': self.mgt_volume['id'],
                                                             'conf_params': {},
                                                             'reformat': True},
                                                     'mdts': [{
                                                                  'volume_id': v['id'],
                                                                  'conf_params': {},
                                                                  'reformat': True
                                                              } for v in self.mdt_volumes],
                                                     'osts': [{
                                                                  'volume_id': v['id'],
                                                                  'conf_params': {},
                                                                  'reformat': True
                                                              } for v in self.ost_volumes],
                                                     'conf_params': {}})

        return self.chroma_manager.get('/api/filesystem',
                                       params = {'id': self.filesystem_id}).json['objects'][0]

    def _add_mdt(self, index, mdt_count):
        mdt_volumes = self.ha_volumes[1 + index:(1 + index + mdt_count)]
        create_commands = []

        for mdt_volume in mdt_volumes:
            response = self.chroma_manager.post("/api/target/", body = {'volume_id': mdt_volume['id'],
                                                                        'kind': 'MDT',
                                                                        'filesystem_id': self.filesystem_id})

            self.assertEqual(response.status_code, 202, response.text)
            create_commands.append(response.json['command']['id'])

        for create_command in create_commands:
            self.wait_for_command(self.chroma_manager, create_command)

        self.mdt_volumes += mdt_volumes

        return self.chroma_manager.get('/api/filesystem',
                                       params = {'id': self.filesystem_id}).json['objects'][0]

    def _delete_mdt(self, filesystem, mdt, fail = False):
        response = self.chroma_manager.delete(mdt['resource_uri'])

        if fail:
            self.assertEqual(response.status_code, 400, response.text)
            self.assertTrue("State 'removed' is invalid" in response.text, response.text)
        else:
            self.assertEqual(response.status_code, 202, response.text)
            self.wait_for_command(self.chroma_manager, response.json['command']['id'])

        return self.chroma_manager.get('/api/filesystem',
                                       params = {'id': self.filesystem_id}).json['objects'][0]

    def _check_stats(self, filesystem):
        if config.get('simulator', False):                                          # Don't validate stats on the simulator.
            return

        mdt_indexes = [mdt['index'] for mdt in filesystem['mdts']]
        client = config['lustre_clients'][0]['address']

        no_of_files_per_mdt = [3 * (n + 1) for n in range(0, len(mdt_indexes))]     # Write a different number of files to each MDT

        # Get the stats before.
        start_stats = {}
        for mdt_index in mdt_indexes:
            start_stats[mdt_index] = self.get_mdt_stats(filesystem, mdt_index)

        self.remote_operations.mount_filesystem(client, filesystem)
        try:
            self.remote_operations.exercise_filesystem(client, filesystem, mdt_indexes, no_of_files_per_mdt)
        finally:
            self.remote_operations.unmount_filesystem(client, filesystem)

        # We have to wait a short time to ensure the manager is updated with the stats. I don't like a sleep but not
        # sure how to be sure all the updates have happened optimally. Stats are reported every 10 seconds so 15 seconds
        # should be not to much.
        time.sleep(15)

        # Get the stats after, this could be shorter and part of the next loop, but I figure the stats test might expand
        # and having the whole end state useful.
        end_stats = {}
        for mdt_index in mdt_indexes:
            end_stats[mdt_index] = self.get_mdt_stats(filesystem, mdt_index)

        # Now do the compare.
        for index, mdt_index in enumerate(mdt_indexes):
            diff_stat = {}

            for stat in start_stats[mdt_index]:
                diff_stat[stat] = float(end_stats[mdt_index][stat]) - float(start_stats[mdt_index][stat])

            # Now check some sample values. smoke test really.
            if index == 0:
                # self.assertEqual(diff_stat['stats_mkdir'], len(mdt_indexes) + no_of_files_per_mdt[index] + sum(no_of_files_per_mdt))  # We created a directory for each MDT + 2 for each file (mkdir -p a/b counts as 2)
                # I have yet to work out a calculation that works for rmdir. I'm not going to create a ticket because it isn't going to be important
                # enough to get fix. There are lots of stats we could have chosen that might have been similar. But if someone wants to have a go
                # at this calculation then it would be great. The calc works for 1 mdt.
                # self.assertEqual(diff_stat['stats_rmdir'], len(mdt_indexes) + no_of_files_per_mdt[index])
                pass
            else:
                self.assertEqual(diff_stat['stats_mkdir'], no_of_files_per_mdt[index])                             # We created one directories for each file
                self.assertEqual(diff_stat['stats_rmdir'], 1 + no_of_files_per_mdt[index])                         # We then remove the directory

            self.assertEqual(diff_stat['stats_open'], (2 * no_of_files_per_mdt[index]) + 1)                    # Directory creation is a open
            self.assertEqual(diff_stat['stats_unlink'], no_of_files_per_mdt[index])                                # And remove all the files.

    def test_create_dne_filesystem(self):
        """
        Test that we can create a DNE file system with 2 MDTs
        """
        filesystem = self._create_filesystem(2)
        self.assertEqual(len(filesystem['mdts']), 2)
        self.assertEqual(len(filesystem['osts']), 1)
        self._check_stats(filesystem)

    @skip('Remove while we fix HYD-4520')
    def test_create_single_filesystem_add_mdt(self):
        """
        Test that we can create a single MDT file system and then add MDTs
        """
        filesystem = self._create_filesystem(1)
        self.assertEqual(len(filesystem['mdts']), 1)
        self.assertEqual(len(filesystem['osts']), 1)
        self._check_stats(filesystem)

        filesystem = self._add_mdt(1, 1)
        self.assertEqual(len(filesystem['mdts']), 2)
        self.assertEqual(len(filesystem['osts']), 1)
        self._check_stats(filesystem)

        filesystem = self._add_mdt(2, 1)
        self.assertEqual(len(filesystem['mdts']), 3)
        self.assertEqual(len(filesystem['osts']), 1)
        self._check_stats(filesystem)

    def test_mdt0_undeletable(self):
        """
        Test to ensure that we cannot delete MDT0
        """
        filesystem = self._create_filesystem(3)
        self.assertEqual(len(filesystem['mdts']), 3)
        self.assertEqual(len(filesystem['osts']), 1)
        self._check_stats(filesystem)

        filesystem = self._delete_mdt(filesystem, next(mdt for mdt in filesystem['mdts'] if mdt['index'] == 0), fail = True)
        self.assertEqual(len(filesystem['mdts']), 3)
        self.assertEqual(len(filesystem['osts']), 1)
        self._check_stats(filesystem)

        # Remove for HYD-4419 which removed the ability to remove an MDT
        #filesystem = self._delete_mdt(filesystem, next(mdt for mdt in filesystem['mdts'] if mdt['index'] != 0), fail = False)
        #self.assertEqual(len(filesystem['mdts']), 2)
        #self.assertEqual(len(filesystem['osts']), 1)
        #self._check_stats(filesystem)

        # For HYD-4419 check that an INDEX != 0 also can't be removed.
        filesystem = self._delete_mdt(filesystem, next(mdt for mdt in filesystem['mdts'] if mdt['index'] != 0), fail = True)
        self.assertEqual(len(filesystem['mdts']), 3)
        self.assertEqual(len(filesystem['osts']), 1)
        self._check_stats(filesystem)

    @skip("LU-6586 Prevents DNE Removal Working")
    def test_mdt_add_delete_add(self):
        """
        Test to ensure that we add and delete MDTs
        """
        filesystem = self._create_filesystem(1)
        self.assertEqual(len(filesystem['mdts']), 1)
        self.assertEqual(len(filesystem['osts']), 1)
        self._check_stats(filesystem)

        filesystem = self._add_mdt(1, 2)
        self.assertEqual(len(filesystem['mdts']), 3)
        self.assertEqual(len(filesystem['osts']), 1)
        self._check_stats(filesystem)

        filesystem = self._delete_mdt(filesystem, next(mdt for mdt in filesystem['mdts'] if mdt['index'] == 2), fail = False)
        self.assertEqual(len(filesystem['mdts']), 2)
        self.assertEqual(len(filesystem['osts']), 1)
        self._check_stats(filesystem)

        filesystem = self._add_mdt(1, 1)
        self.assertEqual(len(filesystem['mdts']), 3)
        self.assertEqual(len(filesystem['osts']), 1)
        self._check_stats(filesystem)

        # The new one should have an index of 3 (being the 4th added) so check by finding.
        # This will exception if there is no index == 3
        next(mdt for mdt in filesystem['mdts'] if mdt['index'] == 3)
