

import logging
import socket
import time
import paramiko
import re
from testconfig import config
from tests.integration.core.constants import TEST_TIMEOUT
from tests.integration.core.utility_testcase import RemoteCommandResult


logger = logging.getLogger('test')
logger.setLevel(logging.DEBUG)


class RemoteOperations(object):
    """
    Actions occuring 'out of band' with respect to chroma manager, usually
    things which talk directly to a storage server or a lustre client rather
    than going via the chroma manager API.
    """

    def _address2server(self, address):
        for server in config['lustre_servers']:
            if server['address'] == address:
                return server

        raise RuntimeError('Unable to resolve %s as a server fqdn' % address)


class SimulatorRemoteOperations(RemoteOperations):
    def __init__(self, test_case, simulator):
        self._test_case = test_case
        self._simulator = simulator

    def host_contactable(self, address):
        cfg_server = self._address2server(address)
        sim_server = self._simulator.servers[cfg_server['fqdn']]
        if sim_server.running:
            return not sim_server.starting_up and not sim_server.shutting_down
        else:
            return False

    def stop_target(self, fqdn, ha_label):
        self._simulator.get_cluster(fqdn).stop(ha_label)

    def start_target(self, fqdn, ha_label):
        self._simulator.get_cluster(fqdn).start(ha_label)

    def start_lnet(self, fqdn):
        self._simulator.servers[fqdn].start_lnet()

    def stop_lnet(self, fqdn):
        self._simulator.servers[fqdn].stop_lnet()

    def read_proc(self, address, path):
        fqdn = None
        for server in config['lustre_servers']:
            if server['address'] == address:
                fqdn = server['fqdn']

        if fqdn is None and not address in config['lustre_clients']:
            raise KeyError("No server with address %s" % address)
        elif fqdn is None and address in config['lustre_clients']:
            client = self._simulator.get_lustre_client(address)
            return client.read_proc(path)
        else:
            return self._simulator.servers[fqdn].read_proc(path)

    def mount_filesystem(self, client_address, filesystem):
        client = self._simulator.get_lustre_client(client_address)
        mgsnode, fsname = filesystem['mount_path'].split(":/")
        client.mount(mgsnode, fsname)

    def unmount_filesystem(self, client_address, filesystem):
        client = self._simulator.get_lustre_client(client_address)
        mgsnode, fsname = filesystem['mount_path'].split(":/")
        client.unmount(mgsnode, fsname)

    def get_resource_running(self, host, ha_label):
        actual = self._simulator.get_cluster(host['fqdn']).resource_locations()[ha_label]
        expected = host['nodename']
        logger.debug("get_resource_running: %s %s %s" % (ha_label, actual, expected))
        return actual == expected

    def check_ha_config(self, hosts, filesystem):
        # TODO check self._simulator.get_cluster(fqdn) for some resources
        # configured on these hosts withthe filesystem name in them
        pass

    def exercise_filesystem(self, client_address, filesystem):
        # TODO: do a check that the client has the filesystem mounted
        # and that the filesystem targets are up
        pass

    def kill_server(self, fqdn):
        self._simulator.stop_server(fqdn, shutdown = True)

    def await_server_boot(self, boot_fqdn, monitor_fqdn = None, restart = True):
        server = self._simulator.servers[boot_fqdn]
        if not server.registered:
            logger.warn("Can't start %s; not registered" % boot_fqdn)
            return

        restart_attempted = False
        running_time = 0
        while not self.host_contactable(boot_fqdn) and running_time < TEST_TIMEOUT:
            # Restart signals that a stopped server should be restarted here.
            # Otherwise, we'll just wait for it to (re-)boot, hoping that this
            # was initiated elsewhere.
            if restart and not restart_attempted:
                restart_attempted = True
                self._simulator.start_server(boot_fqdn)

            running_time += 1
            time.sleep(1)

        self._test_case.assertLess(running_time, TEST_TIMEOUT, "Timed out waiting for %s to boot" % boot_fqdn)

    def unmount_clients(self):
        self._simulator.unmount_lustre_clients()

    def clear_ha(self):
        self._simulator.clear_clusters()

    def inject_log_message(self, fqdn, message):
        self._simulator.servers[fqdn].inject_log_message(message)


class RealRemoteOperations(RemoteOperations):
    def __init__(self, test_case):
        self._test_case = test_case

    # TODO: reconcile this with the one in UtilityTestCase, ideally all remote
    # operations would flow through here to avoid rogue SSH calls
    def _ssh_address(self, address, command, expected_return_code=0, timeout=TEST_TIMEOUT,
                     ssh_key_file=None):
        """
        Executes a command on a remote server over ssh.

        Sends a command over ssh to a remote machine and returns the stdout,
        stderr, and exit status. It will verify that the exit status of the
        command matches expected_return_code unless expected_return_code=None.
        """
        logger.debug("remote_command[%s, keyfile=%s]: %s" % (address, ssh_key_file, command))
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(address, **{'username': 'root', 'key_filename': ssh_key_file})
        transport = ssh.get_transport()
        transport.set_keepalive(20)
        channel = transport.open_session()
        channel.settimeout(timeout)
        channel.exec_command(command)
        stdout = channel.makefile('rb')
        stderr = channel.makefile_stderr()
        exit_status = channel.recv_exit_status()
        if expected_return_code is not None:
            self._test_case.assertEqual(exit_status, expected_return_code, stderr.read())
        return RemoteCommandResult(exit_status, stdout, stderr)

    def _ssh_fqdn(self, fqdn, command, expected_return_code = 0, timeout = TEST_TIMEOUT):
        address = None
        for host in config['lustre_servers']:
            if host['fqdn'] == fqdn:
                address = host['address']
        if address is None:
            raise KeyError(fqdn)

        return self._ssh_address(address, command, expected_return_code, timeout)

    def stop_target(self, fqdn, ha_label):
        self._ssh_fqdn(fqdn, "chroma-agent stop_target --ha %s" % ha_label)

    def start_target(self, fqdn, ha_label):
        self._ssh_fqdn(fqdn, "chroma-agent start_target --ha %s" % ha_label)

    def stop_lnet(self, fqdn):
        self._ssh_fqdn(fqdn, "chroma-agent stop_lnet")

    def start_lnet(self, fqdn):
        self._ssh_fqdn(fqdn, "chroma-agent start_lnet")

    def inject_log_message(self, fqdn, message):
        self._ssh_fqdn(fqdn, "logger \"%s\"" % message)

    def read_proc(self, address, path):
        result = self._ssh_address(address, "cat %s" % path)
        return result.stdout.read().strip()

    def mount_filesystem(self, client_address, filesystem):
        """
        Mounts a lustre filesystem on a specified client.
        """
        self._ssh_address(
            client_address,
            "mkdir -p /mnt/%s" % filesystem['name']
        )

        self._ssh_address(
            client_address,
            filesystem['mount_command']
        )

        result = self._ssh_address(
            client_address,
            'mount'
        )
        self._test_case.assertRegexpMatches(
            result.stdout.read(),
            "%s on /mnt/%s " % (filesystem['mount_path'], filesystem['name'])
        )

    def _unmount_filesystem(self, client, filesystem_name):
        """
        Unmounts a lustre filesystem from the specified client if mounted.
        """
        result = self._ssh_address(
            client,
            'mount'
        )
        if re.search(" on /mnt/%s " % filesystem_name, result.stdout.read()):
            logger.debug("Unmounting %s" % filesystem_name)
            self._ssh_address(
                client,
                "umount /mnt/%s" % filesystem_name
            )
        result = self._ssh_address(
            client,
            'mount'
        )
        mount_output = result.stdout.read()
        logger.debug("`Mount`: %s" % mount_output)
        self._test_case.assertNotRegexpMatches(
            mount_output,
            " on /mnt/%s " % filesystem_name
        )

    def unmount_filesystem(self, client_address, filesystem):
        """
        Unmounts a lustre filesystem from the specified client if mounted.
        """
        self._unmount_filesystem(client_address, filesystem['name'])

    def get_resource_running(self, host, ha_label):
        result = self._ssh_address(
            host['address'],
            'crm_resource -r %s -W' % ha_label,
            timeout = 30  # shorter timeout since shouldnt take long and increases turnaround when there is a problem
        )
        resource_status = result.stdout.read()

        # Sometimes crm_resource -W gives a false positive when it is repetitively
        # trying to restart a resource over and over. Lets also check the failcount
        # to check that it didn't have problems starting.
        result = self._ssh_address(
            host['address'],
            'crm_attribute -t status -n fail-count-%s -N %s -G -d 0' % (ha_label, host['nodename'])
        )
        self._test_case.assertRegexpMatches(
            result.stdout.read(),
            'value=0'
        )

        # Check pacemaker thinks it's running on the right host.
        expected_resource_status = "%s is running on: %s" % (ha_label, host['nodename'])

        return bool(re.search(expected_resource_status, resource_status))

    def check_ha_config(self, hosts, filesystem):
        for host in hosts:
            result = self._ssh_address(
                host['address'],
                'pcs config'
            )
            configuration = result.stdout.read()
            self._test_case.assertRegexpMatches(
                configuration,
                "\s{2}Resource: %s-MDT0000_.+\n\s{4}Enabled on: %s \(score:20\)\n" %
                (filesystem['name'], host['nodename'])
            )
            self._test_case.assertRegexpMatches(
                configuration,
                " Resource: %s-MDT0000_.+ \(type=Target class=ocf provider=chroma\)\n" %

                filesystem['name']
            )

    def exercise_filesystem(self, client_address, filesystem):
        """
        Verify we can actually exercise a filesystem.

        Currently this only verifies that we can write to a filesystem as a
        sanity check that it was configured correctly.
        """
        # TODO: Expand on this. Perhaps use existing lustre client tests.
        if filesystem.get('bytes_free') is None:
            self._test_case.wait_until_true(lambda: self._test_case.get_filesystem(filesystem['id']).get('bytes_free') is not None)
            filesystem = self._test_case.get_filesystem(filesystem['id'])

        self._ssh_address(
            client_address,
            "dd if=/dev/zero of=/mnt/%s/exercisetest.dat bs=1000 count=%s" % (
                filesystem['name'],
                min((filesystem.get('bytes_free') * 0.4), 512000) / 1000
            )
        )

    def _fqdn_to_server_config(self, fqdn):
        for server in config['lustre_servers']:
            if server['fqdn'] == fqdn:
                return server

        raise RuntimeError("No server config for %s" % fqdn)

    def host_contactable(self, address):
        try:
            #TODO: Better way to check this?
            self._ssh_address(
                address,
                "echo 'Checking if node is ready to receive commands.'"
            )
        except socket.error:
            return False
        except paramiko.AuthenticationException:
            return False
        else:
            return True

    def kill_server(self, fqdn):
        # "Pull the plug" on host
        server_config = self._fqdn_to_server_config(fqdn)
        self._ssh_address(
            server_config['host'],
            server_config['destroy_command'],
            ssh_key_file = None if not server_config['ssh_key_file']
                                else server_config['ssh_key_file']
        )

        i = 0
        while self.host_contactable(server_config['address']):
            i += 1
            time.sleep(1)
            if i > TEST_TIMEOUT:
                raise RuntimeError("Host %s didn't terminate within %s seconds" % (fqdn, TEST_TIMEOUT))

    def await_server_boot(self, boot_fqdn, monitor_fqdn = None, restart = False):
        """
        Wait for the stonithed server to come back online
        """
        boot_server = self._fqdn_to_server_config(boot_fqdn)
        monitor_server = None if monitor_fqdn is None else self._fqdn_to_server_config(monitor_fqdn)
        restart_attempted = False

        running_time = 0
        while running_time < TEST_TIMEOUT:
            if self.host_contactable(boot_server['address']):
                # If we have a peer to check then fall through to that, else
                # drop out here
                if monitor_server:
                    # Verify other host knows it is no longer offline
                    result = self._ssh_address(
                        monitor_server['address'],
                        "crm_mon -1"
                    )
                    node_status = result.stdout.read()
                    if not re.search('Online: \[.* %s .*\]' %
                                     boot_server['nodename'], node_status):
                        break
                else:
                    # No monitor server, take SSH offline-ness as evidence for being booted
                    break
            else:
                if restart and not restart_attempted:
                    logger.info("attempting to restart %s" % boot_fqdn)
                    result = self._ssh_address(
                        boot_server['host'],
                        boot_server['status_command'],
                        ssh_key_file = None if not boot_server['ssh_key_file']
                                            else boot_server['ssh_key_file']
                    )
                    node_status = result.stdout.read()
                    if re.search('running', node_status):
                        logger.info("%s seems to be running, but unresponsive" % boot_fqdn)
                        self.kill_server(boot_fqdn)
                    result = self._ssh_address(
                        boot_server['host'],
                        boot_server['start_command'],
                        ssh_key_file = None if not boot_server['ssh_key_file']
                                            else boot_server['ssh_key_file']
                    )
                    node_status = result.stdout.read()
                    if re.search('started', node_status):
                        logger.info("%s started successfully" % boot_fqdn)
                    restart_attempted = True

            time.sleep(3)
            running_time += 3

        self._test_case.assertLess(running_time, TEST_TIMEOUT, "Timed out waiting for host to come back online.")
        if monitor_server:
            result = self._ssh_address(
                monitor_server['address'],
                "crm_mon -1"
            )
            self._test_case.assertNotRegexpMatches(result.stdout.read(),
                                                   'Online: \[.* %s .*\]' %
                                                   boot_server['nodename'])

    def unmount_clients(self):
        """
        Unmount all filesystems of type lustre from all clients in the config.
        """
        for client in config['lustre_clients'].keys():
            self._ssh_address(
                client,
                'umount -t lustre -a'
            )
            result = self._ssh_address(
                client,
                'mount'
            )
            self._test_case.assertNotRegexpMatches(
                result.stdout.read(),
                " type lustre"
            )

    def has_pacemaker(self, server):
        result = self._ssh_address(
            server['address'],
            'which pcs',
            expected_return_code = None
        )
        return result.exit_status == 0

    def get_pacemaker_targets(self, server):
        """
        Returns a list of chroma targets configured in pacemaker on a server.
        """
        result = self._ssh_address(
            server['address'],
            'crm_resource -L'
        )
        crm_resources = result.stdout.read().split('\n')
        return [r.split()[0] for r in crm_resources if re.search('chroma:Target', r)]

    def is_pacemaker_target_running(self, server, target):
        result = self._ssh_address(
            server['address'],
            "crm_resource -r %s -W" % target

        )
        return re.search('is running', result.stdout.read())

    def clear_ha(self):
        """
        Stops and deletes all chroma targets for any corosync clusters
        configured on any of the lustre servers appearing in the cluster config
        """
        for server in config['lustre_servers']:
            if self.has_pacemaker(server):
                crm_targets = self.get_pacemaker_targets(server)

                # Stop targets and delete targets
                for target in crm_targets:
                    self._ssh_address(server['address'], 'pcs resource stop %s' % target)
                for target in crm_targets:
                    self._test_case.wait_until_true(lambda: not self.is_pacemaker_target_running(server, target))
                    self._ssh_address(server['address'], 'pcs resource delete %s' % target)
                    self._ssh_address(server['address'], 'crm_resource -C -r %s' % target)

                # Verify no more targets
                self._test_case.wait_until_true(lambda: not self.get_pacemaker_targets(server))

                # Stop the agent
                self._ssh_address(
                    server['address'],
                    'service chroma-agent stop'
                )
                self._ssh_address(
                    server['address'],
                    'rm -rf /var/lib/chroma/*',
                    expected_return_code = None  # Keep going if it failed - may be none there.
                )
            else:
                logger.info("%s does not appear to have pacemaker - skipping any removal of targets." % server['address'])
