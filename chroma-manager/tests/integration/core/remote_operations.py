import logging
import socket
import time
import datetime
import paramiko
import re
import os
import json

from testconfig import config

from tests.chroma_common.lib.util import ExceptionThrowingThread
from tests.chroma_common.lib.shell import Shell
import sys
from tests.integration.core.constants import TEST_TIMEOUT
from tests.integration.core.constants import RETURN_CODES_CHANNEL_FAIL
from tests.integration.core.constants import LONG_TEST_TIMEOUT
from tests.integration.core.constants import UNATTENDED_BOOT_TIMEOUT
from tests.integration.core.constants import RETURN_CODES_SUCCESS
from tests.integration.core.constants import RETURN_CODES_ALL

logger = logging.getLogger('test')
logger.setLevel(logging.DEBUG)

# paramiko.transport logger spams nose log collection so we're quieting it down
paramiko_logger = logging.getLogger('paramiko.transport')
paramiko_logger.setLevel(logging.WARN)


class RemoteOperations(object):
    """
    Actions occuring 'out of band' with respect to manager, usually
    things which talk directly to a storage server or a lustre client rather
    than going via the manager API.
    """

    def _address2server(self, address):
        for server in config['lustre_servers']:
            if server['address'] == address:
                return server

        raise RuntimeError('Unable to resolve %s as a server fqdn' % address)

    def distro_version(self, host):
        """
        :return: floating point x.y version of distro running. Works for hosts from the api and for the
                 'lustre_servers' type entries in config
        """
        if 'distro' in host:
            return float(re.match('.*([0-9].[0-9])', host['distro']).group(1))
        else:
            return float(json.loads(host['properties'])['distro_version'])


class SimulatorRemoteOperations(RemoteOperations):
    def __init__(self, test_case, simulator):
        self._test_case = test_case
        self._simulator = simulator

    def _not_implemented(self):
        """ Raise exception with template message including name of calling function and current class """
        raise RuntimeError('%s not implemented in %s' % (sys._getframe(1).f_code.co_name, self.__class__))

    def host_contactable(self, address):
        cfg_server = self._address2server(address)
        sim_server = self._simulator.servers[cfg_server['fqdn']]
        if sim_server.running:
            return not sim_server.starting_up and not sim_server.shutting_down
        else:
            return False

    def fail_connections(self, fail):
        """
        Cause all agent attempts at HTTP requests to fail to connect to the manager before
        sending the request.
        """
        # NB could make this more targeted to a specific host
        import requests
        if fail:
            logger.info("Disabling agent connections")
            # Monkey patch requests.request to throw requests.exceptions.ConnectionError
            self._old_request_fn = requests.request

            def fail_connection(*_, **__):
                raise requests.exceptions.ConnectionError("Synthetic connection failure")
            requests.request = fail_connection
        else:
            logger.info("Enabling agent connections")
            # Revert requests.request to its real implementation
            requests.request = self._old_request_fn

    def drop_responses(self, drop):
        """
        Allow the agent to issue one HTTP POST and one HTTP GET, send those requests to the manager,
        drop the responses, and fail outright on subsequent requests.

        This models the case where connectivity is lost in the middle of an HTTP request: the manager
        has built the response, potentially consuming messages which will now be dropped when the agent
        loses the response.
        """
        import requests

        send_request = {
            'get': True,
            'post': True
        }

        if drop:
            logger.info("Dropping responses to agent HTTP requests")
            # Monkey patch requests.request to throw requests.exceptions.ConnectionError
            self._old_request_fn = requests.request

            def drop_response(method, *args, **kwargs):
                try:
                    if send_request[method]:
                        logger.info("drop_response: Letting through first %s" % method)
                        self._old_request_fn(method, *args, **kwargs)
                        send_request[method] = False
                    else:
                        logger.info("drop_response: Dropping subsequent %s" % method)

                finally:
                    raise socket.error("Synthetic connection timeout after issuing request")
            requests.request = drop_response
        else:
            logger.info("Enabling responses to agent HTTP requests")
            # Revert requests.request to its real implementation
            requests.request = self._old_request_fn

    def format_block_device(self, fqdn, path, filesystem_type):
        self._simulator.format_block_device(fqdn, path, filesystem_type)

    def stop_target(self, fqdn, ha_label):
        return self._simulator.get_cluster(fqdn).stop(ha_label)

    def start_target(self, fqdn, ha_label):
        self._simulator.get_cluster(fqdn).start(ha_label)

    def start_lnet(self, fqdn):
        self._simulator.servers[fqdn].start_lnet()

    def stop_lnet(self, fqdn):
        self._simulator.servers[fqdn].stop_lnet()

    def start_pacemaker(self, fqdn):
        self._simulator.servers[fqdn].start_pacemaker()

    def stop_pacemaker(self, fqdn):
        self._simulator.servers[fqdn].stop_pacemaker()

    def start_corosync(self, fqdn):
        self._simulator.servers[fqdn].start_corosync()

    def stop_corosync(self, fqdn):
        self._simulator.servers[fqdn].stop_corosync()

    def restart_chroma_manager(self, fqdn):
        pass

    def get_corosync_port(self, fqdn):
        return self._simulator.servers[fqdn].state['corosync'].mcast_port

    def run_chroma_diagnostics(self, server, verbose):
        return Shell.RunResult(rc=0, stdout="", stderr="", timeout=False)

    def backup_cib(*args, **kwargs):
        return []

    def restore_cib(*args, **kwargs):
        pass

    def set_node_standby(*args, **kwargs):
        pass

    def set_node_online(*args, **kwargs):
        pass

    def read_proc(self, address, path):
        fqdn = None
        for server in config['lustre_servers']:
            if server['address'] == address:
                fqdn = server['fqdn']

        lustre_clients = [c['address'] for c in config['lustre_clients']]
        if fqdn is None and address not in lustre_clients:
            raise KeyError("No server with address %s" % address)
        elif fqdn is None and address in lustre_clients:
            client = self._simulator.get_lustre_client(address)
            return client.read_proc(path)
        else:
            return self._simulator.servers[fqdn].read_proc(path)

    def read_file(self, address, file_path):
        self._not_implemented()

    def rename_file(self, address, current_path, new_path):
        self._not_implemented()

    def create_file(self, address, file_content, file_path):
        self._not_implemented()

    def delete_file(self, address, file_content, file_path):
        self._not_implemented()

    def copy_file(self, address, current_file_path, new_file_path):
        self._not_implemented()

    def file_exists(self, address, file_path):
        self._not_implemented()

    def make_directory(self, address, dir_path):
        self._not_implemented()

    def list_dir(self, address, dir_path):
        self._not_implemented()

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
        expected = host['fqdn']
        logger.debug("get_resource_running: %s %s %s" % (ha_label, actual, expected))
        return actual == expected

    def check_ha_config(self, hosts, filesystem_name):
        # TODO check self._simulator.get_cluster(fqdn) for some resources
        # configured on these hosts withthe filesystem name in them
        pass

    def exercise_filesystem_mdt(self, client_address, filesystem, mdt_index, files_to_create):
        # Lets just imagine we exercised the simulated MDT, go boy go, fetch the ball.
        pass

    def exercise_filesystem(self, client_address, filesystem, mdt_indexes=(0,), no_of_files_per_mdt=None):
        # And the same for the simulated filesystem, 1,2,3,4...1,2,3,4....
        pass

    def clear_lnet_config(self, servers):
        for server in servers:
            self._simulator.servers[server['fqdn']].unconfigure_lnet()

    def reset_server(self, fqdn):
        self._simulator.reboot_server(fqdn)

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

    def unmount_lustre_targets(self, server):
        pass

    def remove_config(self, *args):
        pass

    def write_config(self, *args):
        pass

    def clear_ha(self, servers):
        self._simulator.clear_clusters()

    def inject_log_message(self, fqdn, message):
        self._simulator.servers[fqdn].inject_log_message(message)

    def install_upgrades(self):
        # We don't actually modify the manager here, rather we cause the
        # agents to report that they are seeing higher versions of available
        # packages
        self._simulator.update_packages({
            'lustre': (0, '2.9.0', '1', 'x86_64')
        })

    def get_package_version(self, fqdn, package):
        return self._simulator.servers[fqdn].get_package_version(package)

    def enable_agent_debug(self, server_list):
        # Already handled elsewhere
        pass

    def disable_agent_debug(self, server_list):
        pass

    def sync_disks(self, server_list):
        pass

    def stop_agents(self, server_list):
        pass

    def start_agents(self, server_list):
        pass

    def command(self, address, command, return_codes, timeout, buffer):
        self._not_implemented()

    def execute_commands(self, commands, target, debug_message, return_codes, timeout):
        self._not_implemented()

    def execute_simultaneous_commands(self, commands, targets, debug_message, return_codes, timeout):
        self._not_implemented()


class RealRemoteOperations(RemoteOperations):
    def __init__(self, test_case):
        self._test_case = test_case

    def fail_connections(self, fail):
        # Ways to implement this outside simulation:
        #  * Insert a firewall rule to drop packages between agent and manager
        #  * Stop the management network interface on the storage server
        #  * Switch off the management switch port that the storage server is connected to
        raise NotImplementedError()

    def drop_responses(self, fail):
        # Ways to implement this outside simulation:
        #  * Insert a transparent HTTP proxy between agent and manager, which drops responses
        #  * Use a firewall rule to drop manager->agent TCP streams after N bytes to cause responses
        #    to be mangled.
        raise NotImplementedError()

    def command(self,
                address,
                command,
                return_codes=RETURN_CODES_SUCCESS,
                timeout=TEST_TIMEOUT,
                buffer=None):
        """
        Sends a command over ssh to a remote machine and returns the stdout, stderr and return code.
        It will verify that the return code of the command matches one of return_codes. Address can be an IP or an FQDN.

        :param address: address of targets server to issue ssh command on
        :param command: shell command to issue
        :param return_codes: tuple or list of expected return codes
        :param timeout: time allowed for command to return readable data on stdout (or complete)
        :param buffer: data to supply to stdin when command is issued (file object)
        :return: RunResult object
        """
        logger.debug("command[%s]: %s" % (address, command))
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        args = {'username': 'root'}
        # If given an ssh_config file, require that it defines
        # a private key and username for accessing this host
        config_path = config.get('ssh_config', None)
        if config_path:
            ssh_config = paramiko.SSHConfig()
            ssh_config.parse(open(config_path))

            host_config = ssh_config.lookup(address)
            address = host_config['hostname']

            if 'user' in host_config:
                args['username'] = host_config['user']
                if args['username'] != 'root':
                    command = "sudo sh -c \"{}\"".format(command.replace('"', '\\"'))

            if 'identityfile' in host_config:
                args['key_filename'] = host_config['identityfile'][0]

                # Work around paramiko issue 157, failure to parse quoted values
                # (vagrant always quotes IdentityFile)
                args['key_filename'] = args['key_filename'].strip("\"")

        logger.info("SSH address = %s, args = %s" % (address, args))

        # Create ssh connection
        ssh.connect(address, **args)
        transport = ssh.get_transport()
        transport.set_keepalive(20)
        channel = transport.open_session()
        channel.settimeout(timeout)

        # Actually execute the command
        channel.exec_command(command)
        if buffer:
            stdin = channel.makefile('wb')
            stdin.write(buffer)
            stdin.flush()
            stdin.channel.shutdown_write()

        # Store results. This needs to happen in this order. If recv_exit_status is
        # read first, it can block indefinitely due to paramiko bug #448. The read on
        # the stdout will wait until the command finishes, so its not necessary to have
        # recv_exit_status to block on it first. Closing the channel must come last,
        # or else reading from stdout/stderr will return an empty string.
        stdout = channel.makefile('rb').read()
        stderr = channel.makefile_stderr('rb').read()
        rc = channel.recv_exit_status()
        channel.close()

        # Verify an expected return code was received
        assert rc in return_codes, \
            "expected one of rc: '%s' actual rc: '%s' stdout: '%s' stderr: '%s'" % (return_codes,
                                                                                    rc,
                                                                                    stdout,
                                                                                    stderr)

        return Shell.RunResult(rc, stdout, stderr, timeout=False)

    def execute_commands(self,
                         commands,
                         target,
                         debug_message,
                         return_codes=RETURN_CODES_SUCCESS,
                         timeout=TEST_TIMEOUT):
        """
        Execute a list of commands sequentially on a single target

        :param commands: list of commands to execute on a given target
        :param target: target to execute commands on
        :param debug_message: message to prefix log entry after each command in list is issued
        :param return_codes: tuple or list of expected return codes for each executed command
        :param timeout: timeout in seconds for paramiko ssh channel to receive data
        :return: dictionary of command string keys and result object values
        """
        results = {}
        for command in commands:
            result = self.command(target, command, return_codes, timeout, None)
            logger.info("%s command %s rc %s output:\n %s" % (debug_message, command, result.rc, result.stdout))

            results[command] = result

        return results

    def execute_simultaneous_commands(self,
                                      commands,
                                      targets,
                                      debug_message,
                                      return_codes=RETURN_CODES_SUCCESS,
                                      timeout=TEST_TIMEOUT):
        """
        Execute the same list of commands simultaneously on multiple targets

        :param commands: list of commands to execute on a given target
        :param targets: targets to execute commands on
        :param debug_message: message to prefix log entry after each command in list is issued
        :param return_codes: tuple or list of expected return codes for each executed command
        :param timeout: timeout in seconds for paramiko ssh channel to receive data
        """
        threads = []
        for target in targets:
            command_thread = ExceptionThrowingThread(target=self.execute_commands,
                                                     args=(commands,
                                                           target,
                                                           '%s: %s' % (target, debug_message),
                                                           return_codes,
                                                           timeout))
            command_thread.start()
            threads.append(command_thread)

        map(lambda th: th.join(), threads)

    def format_block_device(self, fqdn, path, filesystem_type):
        commands = {
            'ext2': "mkfs.ext2 -F '{path}'".format(path=path),
            'lustre': "mkfs.lustre --mgs '{path}'".format(path=path)
        }
        try:
            command = commands[filesystem_type]
        except KeyError:
            raise RuntimeError("Unknown filesystem type %s (known types are %s)" % (filesystem_type, commands.keys()))

        self.command(fqdn, command)

    def stop_target(self, fqdn, ha_label):
        return self.command(fqdn, "chroma-agent stop_target --ha %s" % ha_label)

    def start_target(self, fqdn, ha_label):
        self.command(fqdn, "chroma-agent start_target --ha %s" % ha_label)

    def stop_lnet(self, fqdn):
        self.command(fqdn, "chroma-agent stop_lnet")

    def start_lnet(self, fqdn):
        self.command(fqdn, "chroma-agent start_lnet")

    def stop_pacemaker(self, fqdn):
        self.command(fqdn, "chroma-agent stop_pacemaker")

    def start_pacemaker(self, fqdn):
        self.command(fqdn, "chroma-agent start_pacemaker")

    def stop_corosync(self, fqdn):
        self.command(fqdn, "chroma-agent stop_corosync")

    def start_corosync(self, fqdn):
        self.command(fqdn, "chroma-agent start_corosync")

    def restart_chroma_manager(self, fqdn):
        # Do not call this function directly, use restart_chroma_manager in ApiTestCaseWithTestReset class
        self.command(fqdn, 'chroma-config restart')

    def run_chroma_diagnostics(self, server, verbose):
        return self.command(server['fqdn'],
                                   "chroma-diagnostics %s" % ("-v -v -v" if verbose else ""),
                                   timeout=LONG_TEST_TIMEOUT)

    def inject_log_message(self, fqdn, message):
        self.command(fqdn, "logger \"%s\"" % message)

    def read_proc(self, address, path):
        result = self.command(address, "cat %s" % path)
        return result.stdout.strip()

    def read_file(self, address, file_path):
        result = self.command(address, 'cat %s' % file_path)
        return result.stdout

    def rename_file(self, address, current_path, new_path):
        # Warning! This will force move by overwriting destination file
        self.command(address, 'mv -f %s %s' % (current_path, new_path))

    def create_file(self, address, file_content, file_path):
        self.command(address, 'cat > %s <<EOF\n%s\nEOF' % (file_path, file_content))

    def delete_file(self, address, file_path):
        self.command(address, 'rm -rf %s' % file_path)

    def copy_file(self, address, current_file_path, new_file_path):
        self.command(address, 'cp %s %s' % (current_file_path, new_file_path))

    def file_exists(self, address, file_path):
        return self.command(address, 'ls %s' % file_path, return_codes=RETURN_CODES_ALL).rc == 0

    def make_directory(self, address, dir_path):
        self.command(address, 'mkdir %s' % dir_path)

    def list_dir(self, address, dir_path):
        return self.command(address, 'ls %s' % dir_path).stdout.split()

    def cibadmin(self, server, args, buffer=None):
        # -t 1 == time out after 1 sec. of no response
        cmd = "cibadmin -t 1 %s" % args

        tries = 300
        while tries > 0:
            result = self.command(server['fqdn'], cmd, buffer=buffer, return_codes=RETURN_CODES_ALL)

            # retry on expected (i.e. waiting for dust to settle, etc.)
            # failures
            if result.rc not in [10, 41, 62, 107]:
                break
            # don't need a sleep here, the cibadmin timeout provides
            # us with a delay
            tries -= 1

        return result

    def backup_cib(self, server):
        backup = "/tmp/cib-backup-%s.xml" % server['fqdn']
        running_targets = self.get_pacemaker_targets(server, running = True)
        for target in running_targets:
            self.stop_target(server['fqdn'], target)

        self._test_case.wait_until_true(lambda: len(self.get_pacemaker_targets(server, running = True)) < 1)

        with open(backup, "w") as f:
            f.write(self.cibadmin(server, "--query").stdout)

        return running_targets

    def restore_cib(self, server, start_targets):
        import xml.etree.ElementTree as xml

        new_cib = xml.fromstring(open("/tmp/cib-backup-%s.xml" %
                                      server['fqdn']).read())

        # get the current admin_epoch
        current_cib = xml.fromstring(self.cibadmin(server, "--query").stdout)

        new_cib.set('admin_epoch', str(int(current_cib.get('admin_epoch')) + 1))
        new_cib.set('epoch', "0")

        self.cibadmin(server, "--replace --xml-pipe",
                      buffer=xml.tostring(new_cib))

        for target in start_targets:
            self.start_target(server['fqdn'], target)

        self._test_case.wait_until_true(lambda: len(self.get_pacemaker_targets(server, running = True)) == len(start_targets))

    # HYD-2071: These two methods may no longer be useful after the API-side
    # work lands.
    def set_node_standby(self, server):
        self.command(server['address'], "chroma-agent set_node_standby --node %s" % server['fqdn'])

    def set_node_online(self, server):
        self.command(server['address'], "chroma-agent set_node_online --node %s" % server['fqdn'])

    def mount_filesystem(self, client_address, filesystem):
        """
        Mounts a lustre filesystem on a specified client.
        """
        self.command(client_address, "mkdir -p /mnt/%s" % filesystem['name'])

        self.command(client_address, filesystem['mount_command'])

        result = self.command(client_address, 'mount')
        self._test_case.assertRegexpMatches(result.stdout, " on /mnt/%s " % filesystem['name'])

    def _unmount_filesystem(self, client, filesystem_name):
        """
        Unmounts a lustre filesystem from the specified client if mounted.
        """
        result = self.command(client, 'mount')
        if re.search(" on /mnt/%s " % filesystem_name, result.stdout):
            logger.debug("Unmounting %s" % filesystem_name)
            self.command(client, "umount /mnt/%s" % filesystem_name)

        result = self.command(client, 'mount')
        mount_output = result.stdout
        logger.debug("`Mount`: %s" % mount_output)

        self._test_case.assertNotRegexpMatches(mount_output, " on /mnt/%s " % filesystem_name)

    def unmount_filesystem(self, client_address, filesystem):
        """
        Unmounts a lustre filesystem from the specified client if mounted.
        """
        self._unmount_filesystem(client_address, filesystem['name'])

    def get_resource_running(self, host, ha_label):
        # shorter timeout since shouldn't take long and increases turnaround when there is a problem
        result = self.command(host['address'], 'crm_resource -r %s -W' % ha_label, timeout=30)
        resource_status = result.stdout

        # Sometimes crm_resource -W gives a false positive when it is repetitively
        # trying to restart a resource over and over. Lets also check the failcount
        # to check that it didn't have problems starting.
        hostname = host['fqdn'] if self.distro_version(host) >= 7 else host['fqdn'].split('.')[0]
        result = self.command(host['address'],
                              'crm_attribute -t status -n fail-count-%s -N %s -G -d 0' % (ha_label, hostname))

        self._test_case.assertRegexpMatches(result.stdout, 'value=0')

        # Check pacemaker thinks it's running on the right host.
        expected_resource_status = "%s is running on: %s" % (ha_label, host['fqdn'])

        return bool(re.search(expected_resource_status, resource_status))

    def check_ha_config(self, hosts, filesystem_name):
        import xml.etree.ElementTree as xml

        def host_has_location(items, test_host):
            for p in items:
                # Pacemaker shifted from nodename to fqdn after el6.
                if socket.getfqdn(p.attrib['node']) == test_host['fqdn']:
                    return True

            return False

        def has_primitive(items, fs_name):
            for p in items:
                if p.attrib['class'] == "ocf" and \
                   p.attrib['provider'] == "chroma" and \
                   p.attrib['type'] == "Target" and \
                   p.attrib['id'].startswith("%s-" % fs_name):
                    return True
            return False

        for host in hosts:
            result = self.cibadmin(host, '--query')
            configuration = xml.fromstring(result.stdout)

            rsc_locations = configuration.findall('./configuration/constraints/rsc_location')
            self._test_case.assertTrue(host_has_location(rsc_locations, host), configuration)

            primatives = configuration.findall('./configuration/resources/primitive')
            self._test_case.assertTrue(has_primitive(primatives, filesystem_name), configuration)

    def exercise_filesystem_mdt(self, client_address, filesystem, mdt_index, files_to_create):
        """
        Verify we can actually exercise a filesystem on a specific mdt.

        Currently this only verifies that we can write to a filesystem as a
        sanity check that it was configured correctly.
        """
        # TODO: Expand on entire function. Perhaps use existing lustre client tests.

        if not filesystem.get('bytes_free'):
            self._test_case.wait_until_true(lambda: self._test_case.get_filesystem(filesystem['id']).get('bytes_free'))
            filesystem = self._test_case.get_filesystem(filesystem['id'])

        bytes_free = filesystem.get('bytes_free')
        assert bytes_free > 0, "Expected bytes_free to be > 0"
        logger.debug("exercise_filesystem: API reports %s has %s bytes free"
                     % (filesystem['name'], bytes_free))

        test_root = '/mnt/%s/mdt%s' % (filesystem['name'], mdt_index)

        if mdt_index:
            self.command(client_address, "lfs mkdir -i %s %s" % (mdt_index, test_root))
        else:
            self.command(client_address, "mkdir -p %s" % test_root)

        def actual_exercise(client_address, test_root, file_no, bytes_to_write):
            self.command(client_address, "mkdir -p %s/%s" % (test_root, file_no))

            self.command(client_address, "dd if=/dev/zero of=%s/%s/exercisetest-%s.dat bs=1000 count=%s" % (test_root,
                                                                                                            file_no,
                                                                                                            file_no,
                                                                                                            bytes_to_write))

        threads = []

        for file_no in range(0, files_to_create):
            thread = ExceptionThrowingThread(target=actual_exercise,
                                             args=(client_address, test_root, file_no, min((bytes_free * 0.4), 512000) / 1000),
                                             use_threads=False)
            thread.start()
            threads.append(thread)

        ExceptionThrowingThread.wait_for_threads(threads)               # This will raise an exception if any of the threads raise an exception

        self.command(client_address, "rm -rf %s" % test_root)

    def exercise_filesystem(self, client_address, filesystem, mdt_indexes=(0,), no_of_files_per_mdt=None):
        """
        Verify we can actually exercise a filesystem.

        Currently this only verifies that we can write to a filesystem as a
        sanity check that it was configured correctly.
        """

        if not no_of_files_per_mdt:
            no_of_files_per_mdt = [10] * len(mdt_indexes)

        threads = []

        for index, mdt_index in enumerate(mdt_indexes):
            thread = ExceptionThrowingThread(target=self.exercise_filesystem_mdt,
                                             args=(client_address, filesystem, mdt_index, no_of_files_per_mdt[index]))

            thread.start()
            threads.append(thread)

        ExceptionThrowingThread.wait_for_threads(threads)               # This will raise an exception if any of the threads raise an exception

    def _fqdn_to_server_config(self, fqdn):
        for server in config['lustre_servers']:
            if server['fqdn'] == fqdn:
                return server

        raise RuntimeError("No server config for %s" % fqdn)

    def host_contactable(self, address):
        try:
            # TODO: Better way to check this?
            result = self.command(address,
                                  "echo 'Checking if node is ready to receive commands.'",
                                  return_codes=RETURN_CODES_ALL)

        except socket.error:
            logger.debug("Unknown socket error when checking %s" % address)
            return False
        except paramiko.AuthenticationException, e:
            logger.debug("Auth error when checking %s: %s" % (address, e))
            return False
        except paramiko.SSHException, e:
            logger.debug("General SSH error when checking %s: %s" % (address, e))
            return False
        except EOFError:
            logger.debug("Connection unexpectedly killed while checking %s" % address)
            return False

        if not result.rc == 0:
            # Wait, what?  echo returned !0?  How is that possible?
            logger.debug("exit status %d from echo on %s: inconceivable!" % (result.rc, address))
            return False

        return True

    def host_up_secs(self, address):
        result = self.command(address, "cat /proc/uptime")
        secs_up = result.stdout.split()[0]
        return secs_up

    def _host_of_server(self, server):
        return config['hosts'][server['host']]

    def reset_server(self, fqdn):
        # NB: This is a vaguely dangerous operation -- basically the
        # equivalent of hitting the reset button. It's not a nice
        # shutdown that gives the fs time to sync, etc.
        server_config = self._fqdn_to_server_config(fqdn)
        host = self._host_of_server(server_config)
        reset_cmd = server_config.get('reset_command', None)
        if host.get('reset_is_buggy', False):
            self.kill_server(fqdn)
            self.start_server(fqdn)
        elif reset_cmd:
            result = self.command(server_config['host'], reset_cmd, ssh_key_file=server_config.get('ssh_key_file', None))
            node_status = result.stdout
            if re.search('was reset', node_status):
                logger.info("%s reset successfully" % fqdn)
        else:
            self.command(server_config['address'],
                         """
                         echo 1 > /proc/sys/kernel/sysrq;
                         echo b > /proc/sysrq-trigger
                         """, return_codes=RETURN_CODES_CHANNEL_FAIL)

    def kill_server(self, fqdn):
        # "Pull the plug" on host
        server_config = self._fqdn_to_server_config(fqdn)
        self.command(server_config['host'], server_config['destroy_command'])

        i = 0
        last_secs_up = 0
        while self.host_contactable(server_config['address']):
            # plug a race where the host comes up fast enough to allow ssh to
            # plow through
            secs_up = self.host_up_secs(server_config['address'])
            if secs_up < last_secs_up:
                return

            last_secs_up = secs_up

            i += 1
            time.sleep(1)
            if i > TEST_TIMEOUT:
                raise RuntimeError("Host %s didn't terminate within %s seconds" % (fqdn, TEST_TIMEOUT))

    def start_server(self, fqdn):
        boot_server = self._fqdn_to_server_config(fqdn)

        node_status = self.command(boot_server['host'], boot_server['start_command']).stdout

        if re.search('started', node_status):
            logger.info("%s started successfully" % fqdn)

    def await_server_boot(self, boot_fqdn, monitor_fqdn=None, restart=False):
        """ Wait for the stonithed server to come back online """
        boot_server = self._fqdn_to_server_config(boot_fqdn)
        monitor_server = None if monitor_fqdn is None else self._fqdn_to_server_config(monitor_fqdn)
        restart_attempted = False

        hostname = boot_server['fqdn'] if self.distro_version(boot_server) >= 7 else boot_server['fqdn'].split('.')[0]

        running_time = 0
        while running_time < TEST_TIMEOUT:
            if self.host_contactable(boot_server['address']):
                # If we have a peer to check then fall through to that, else
                # drop out here
                if monitor_server:
                    # Verify other host knows it is no longer offline
                    result = self.command(monitor_server['address'], "crm_mon -1")
                    node_status = result.stdout

                    logger.info("Response running crm_mon -1 on %s:  %s" % (hostname, node_status))
                    err = result.stderr
                    if err:
                        logger.error("    result.stderr:  %s" % err)
                    if re.search('Online: \[.* %s .*\]' % hostname, node_status):
                        break
                else:
                    # No monitor server, take SSH offline-ness as evidence for being booted
                    break
            else:
                if restart and running_time > UNATTENDED_BOOT_TIMEOUT and \
                   not restart_attempted:
                    logger.info("attempting to restart %s" % boot_fqdn)
                    result = self.command(boot_server['host'], boot_server['status_command'])
                    node_status = result.stdout
                    if re.search('running', node_status):
                        logger.info("%s seems to be running, but unresponsive" % boot_fqdn)
                        self.kill_server(boot_fqdn)
                    self.start_server(boot_fqdn)
                    restart_attempted = True

            time.sleep(3)
            running_time += 3

        if running_time >= TEST_TIMEOUT:
            host_alive = self.command(boot_server['address'], 'hostname', return_codes=RETURN_CODES_ALL).rc == 0

            self._test_case._fetch_help(lambda: self._test_case.assertTrue(False,
                                                                           "Timed out waiting for host %s to come back online.\n"
                                                                           "Host is actually alive %s" % (hostname, host_alive)),
                                        ['chris.gearing@intel.com'])

        if monitor_server:
            result = self.command(monitor_server['address'], "crm_mon -1")
            self._test_case.assertRegexpMatches(result.stdout, 'Online: \[.* %s .*\]' % hostname)

    def unmount_clients(self):
        """
        Unmount all filesystems of type lustre from all clients in the config.
        """
        for client in config['lustre_clients'] + self.config_workers:
            self.command(client['address'], 'umount -t lustre -a')
            self.command(client['address'], 'sed -i \'/lustre/d\' /etc/fstab')

            if client not in [server['address'] for server in config['lustre_servers']]:
                # Skip this check if the client is also a server, because
                # both targets and clients look like 'lustre' mounts
                result = self.command(client['address'], 'mount')
                self._test_case.assertNotRegexpMatches(result.stdout, " type lustre")

    def unmount_lustre_targets(self, server):
        """
        Unmount all the lustre targets on the server passed.

        :param server: Target server
        :return: Exception on failure.
        """
        try:
            self.command(server['address'], 'umount -t lustre -a')
        except socket.timeout:
            # Uh-oh.  Something bad is happening with Lustre.  Let's see if
            # we can gather some information for the LU team.
            logger.info("Unmounting Lustre on %s timed out.  Going to try to gather debug information." % server['fqdn'])
            self.command(server['address'],
                         """set -ex
                         echo 1 > /proc/sys/kernel/sysrq
                         echo 8 > /proc/sysrq-trigger
                         echo t > /proc/sysrq-trigger
                         """)
            # going to need to reboot this node to get any use out of it
            self.reset_server(server['fqdn'])
            raise RuntimeError("Failed to umount Lustre on %s.  Debug data has been collected.  "
                               "Make sure to add it to an existing ticket or create a new one." % server['fqdn'])

    def is_worker(self, server):
        workers = [w['address'] for w in
                   config['lustre_servers'] if 'worker' in w.get('profile', "")]
        return server['address'] in workers

    @property
    def config_workers(self):
        return [w for w in config['lustre_servers'] if self.is_worker(w)]

    def has_pacemaker(self, server):
        return self.command(server['address'], 'which crmadmin', return_codes=RETURN_CODES_ALL).rc == 0

    def get_pacemaker_targets(self, server, running=False):
        """
        Returns a list of chroma targets configured in pacemaker on a server.
        :param running: Restrict the returned list only to running targets.
        """
        result = self.command(server['address'], 'crm_resource -L')
        crm_resources = result.stdout.split('\n')
        targets = []
        for r in crm_resources:
            if not re.search('chroma:Target', r):
                continue

            target = r.split()[0]
            if running and re.search('Started\s*$', r):
                targets.append(target)
            elif not running:
                targets.append(target)
        return targets

    def is_pacemaker_target_running(self, server, target):
        return re.search('is running', self.command(server['address'], "crm_resource -r %s -W" % target).stdout)

    def get_fence_nodes_list(self, address):
        result = self.command(address, "fence_chroma -o list")
        # -o list returns:
        # host1,\n
        # host2,\n
        # ...
        # List is fqdns on el7, short names on el6, normalised to always contain fqdns
        return [socket.getfqdn(node) for node in result.stdout.split(',\n') if node]

    def remove_config(self, server_list):
        """
        Remove /etc/chroma.cfg on the test servers.
        """
        for server in server_list:
            self.command(server['address'], 'rm -f /etc/chroma.cfg')

    def write_config(self, server_list):
        """
        Write out /etc/chroma.cfg on the test servers.
        """
        from ConfigParser import SafeConfigParser
        from StringIO import StringIO

        sections = ['corosync']

        for server in server_list:
            config = SafeConfigParser()
            for section in sections:
                config_key = "%s_config" % section
                if config_key in server:
                    config.add_section(section)
                    for key, val in server[config_key].items():
                        config.set(section, key, val)
            cfg_str = StringIO()
            config.write(cfg_str)

            if len(cfg_str.getvalue()) > 0:
                self.command(server['address'], 'cat > /etc/chroma.cfg', buffer=cfg_str.getvalue())

        self.sync_disks([s['address'] for s in server_list])

    def sync_disks(self, server_list):
        """
        Runs a 'sync' on the targeted server(s) to ensure that caches
        are flushed. Usually not necessary, but can help to avoid races
        between configs getting to disk and powercycle operations.
        """
        for server in server_list:
            self.command(server, 'sync; sync')

    def stop_agents(self, server_list):
        for server in server_list:
            self.command(server, '/etc/init.d/chroma-agent stop')

    def start_agents(self, server_list):
        for server in server_list:
            self.command(server, '/etc/init.d/chroma-agent start')

    def catalog_rpms(self, server_list, location, sorted=False):
        """
        Runs an 'rpm -qa' on the targeted server(s) redirecting the
        output into the named file, optionally piped through sort
        """
        sort_cmd = ""
        if sorted:
            sort_cmd = " | sort"
        for server in server_list:
            self.command(server, 'rpm -qa %s > %s' % (sort_cmd, location))

    def clear_ha(self, server_list):
        """
        Stops and deletes all chroma targets for any corosync clusters
        configured on any of the lustre servers appearing in the cluster config
        """
        for server in server_list:
            address = server['address']

            if self.is_worker(server):
                logger.info("%s is configured as a worker -- skipping." % server['address'])
                continue

            if self.has_pacemaker(server):
                from tests.utils.remote_firewall_control import RemoteFirewallControl
                firewall = RemoteFirewallControl.create(address)

                if config.get('pacemaker_hard_reset', False):
                    clear_ha_script_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                        "clear_ha_el%s.sh" % re.search('\d', server['distro']).group(0))

                    with open(clear_ha_script_file, 'r') as clear_ha_script:
                        self.command(address, clear_ha_script.read())

                    self.command(address, firewall.remote_add_port_cmd(22, 'tcp'))
                    self.command(address, firewall.remote_add_port_cmd(988, 'tcp'))

                    self.unmount_lustre_targets(server)
                else:
                    crm_targets = self.get_pacemaker_targets(server)

                    # Stop targets and delete targets
                    for target in crm_targets:
                        self.command(address, 'crm_resource --resource %s --set-parameter target-role --meta --parameter-value Stopped' % target)
                    for target in crm_targets:
                        self._test_case.wait_until_true(lambda: not self.is_pacemaker_target_running(server, target))
                        self.command(address, 'pcs resource delete %s' % target)
                        self.command(address, 'crm_resource -C -r %s' % target)

                    # Verify no more targets
                    self._test_case.wait_until_true(lambda: not self.get_pacemaker_targets(server))

                    # remove firewall rules previously added for corosync
                    mcast_port = self.get_corosync_port(server['fqdn'])
                    if mcast_port:
                        self.command(address, firewall.remote_remove_port_cmd(mcast_port, 'udp'))
            else:
                logger.info("%s does not appear to have pacemaker - skipping any removal of targets." % address)

            if self.command(address, "rpm -q chroma-agent", return_codes=RETURN_CODES_ALL).rc == 0:
                # Stop the agent
                self.command(address, 'service chroma-agent stop')
                # Keep going if it failed - may be none there.

                self.command(address, 'rm -rf /var/lib/chroma/*', return_codes=RETURN_CODES_ALL)

    def clear_lnet_config(self, server_list):
        """
        Removes the lnet configuration file for the server list passed.
         """

        # This isn't really that bad because the file will not be recreated if I delete it so probably ammounts
        # to at most an extra reboot cycle per test session.
        # Note the sleep ensures the reboot really happens otherwise it might look alive in the await_server_boot
        for server in server_list:
            # Keep going if it failed - may be none there.
            self.command(server['address'],
                         "[ -f /etc/modprobe.d/iml_lnet_module_parameters.conf ] && "
                         "rm -f /etc/modprobe.d/iml_lnet_module_parameters.conf && reboot && sleep 20",
                         return_codes=RETURN_CODES_ALL)

        # Now ensure they have all comeback to life
        for server in server_list:
            self.await_server_boot(server['fqdn'], restart=True)

    def install_upgrades(self):
        raise NotImplementedError("Automated test of upgrades is HYD-1739")

    def get_package_version(self, fqdn, package):
        raise NotImplementedError("Automated test of upgrades is HYD-1739")

    def get_corosync_port(self, fqdn):
        mcast_port = None
        for line in self.command(fqdn, "cat /etc/corosync/corosync.conf || true").stdout.split('\n'):

            match = re.match("\s*mcastport:\s*(\d+)", line)
            if match:
                mcast_port = match.group(1)
                break

        return int(mcast_port) if mcast_port is not None else None

    def grep_file(self, server, string, file):
        result = self.command(server['address'], "grep -e \"%s\" %s || true" % (string, file)).stdout
        return result

    def get_file_content(self, server, file):
        result = self.command(server['address'], "cat \"%s\" || true" % file).stdout
        return result

    def enable_agent_debug(self, server_list):
        for server in server_list:
            self.command(server['address'], "touch /tmp/chroma-agent-debug")

    def disable_agent_debug(self, server_list):
        for server in server_list:
            self.command(server['address'], "rm -f /tmp/chroma-agent-debug")

    def omping(self, server, servers, count=5, timeout=30):
        from tests.utils.remote_firewall_control import RemoteFirewallControl
        firewall = RemoteFirewallControl.create(server['address'])

        self.command(server['address'], firewall.remote_add_port_cmd(4321, 'udp'))

        result = self.command(server['address'],
                              'exec 2>&1; omping -T %s -c %s %s' % (timeout,
                                                                    count,
                                                                    " ".join([s['fqdn'] for s in servers])))

        self.command(server['address'], firewall.remote_remove_port_cmd(4321, 'udp'))

        return result.stdout

    def yum_update(self, server):
        self.command(server['address'], "yum -y update")

    def default_boot_kernel_path(self, server):
        r = self.command(server['address'], "grubby --default-kernel")
        stdout = r.stdout.rstrip()

        return stdout

    def get_chroma_repos(self):
        result = self.command(config['chroma_managers'][0]['address'], "ls /var/lib/chroma/repo/")
        return result.stdout.split()

    def check_time_within_range(self, first_dt, second_dt, minutes):
        """check if first_dt datetime value is within 'minutes' of the second_dt"""
        min_dt = second_dt - datetime.timedelta(minutes=minutes)
        max_dt = second_dt + datetime.timedelta(minutes=minutes)

        return min_dt < first_dt < max_dt

    def get_server_time(self, client_address):
        """return datetime.datetime from UTC date on client"""
        _date_get_format = '%Y:%m:%d:%H:%M'

        time_string = self.command(client_address, 'date -u +%s' % _date_get_format).stdout.strip('\n')

        # create datetime.datetime from linux date utility shell output
        return datetime.datetime(*[int(element) for element in time_string.split(':')])

    def set_server_time(self, client_address, new_datetime):
        """set client date & time with date utility, use utility defined format"""
        _date_set_format = '%Y%m%d %H:%M'

        time_string = new_datetime.strftime(_date_set_format)
        result = self.command(client_address, 'date -u --set="%s"' % time_string)

        return result
