import logging
import socket
import time
import datetime
import paramiko
import re
import os
import json
import subprocess

from testconfig import config

from iml_common.lib.util import ExceptionThrowingThread
from iml_common.lib.shell import Shell
from tests.utils.remote_firewall_control import RemoteFirewallControl
from tests.unit.constants import TEST_TIMEOUT
from tests.unit.constants import LONG_TEST_TIMEOUT

logger = logging.getLogger("test")
logger.setLevel(logging.DEBUG)

stop_agent_cmd = """
    systemctl stop iml-storage-server.target
    i=0

    while systemctl status chroma-agent && [ "$i" -lt {timeout} ]; do
        ((i++))
        sleep 1
    done

    if [ "$i" -eq {timeout} ]; then
        exit 1
    fi
    """.format(
    timeout=TEST_TIMEOUT
)


class RemoteOperations(object):
    """
    Actions occuring 'out of band' with respect to manager, usually
    things which talk directly to a storage server or a lustre client rather
    than going via the manager API.
    """

    def get_fence_nodes_list(self, address, ignore_failure=False):
        return ["fake", "fake"]


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

    def _ssh_address_no_check(self, address, command_string):
        """ pass _ssh_address expected_return_code=None, so exception not raised on nonzero return code """
        return self._ssh_address(address, command_string, expected_return_code=None)

    # TODO: reconcile this with the one in UtilityTestCase, ideally all remote
    # operations would flow through here to avoid rogue SSH calls
    def _ssh_address(self, address, command, expected_return_code=0, timeout=TEST_TIMEOUT, buffer=None, as_root=True):
        """
        Executes a command on a remote server over ssh.

        Sends a command over ssh to a remote machine and returns the stdout,
        stderr, and exit status. It will verify that the exit status of the
        command matches expected_return_code unless expected_return_code=None.
        """

        def host_test(address, issue_num):
            def print_result(r):
                return "rc: %s\n\nstdout:\n%s\n\nstderr:\n%s" % (r.rc, r.stdout, r.stderr)

            ping_result1 = Shell.run(["ping", "-c", "1", "-W", "1", address])
            ping_result2_report = ""
            ip_addr_result = Shell.run(["ip", "addr", "ls"])
            ip_route_ls_result = Shell.run(["ip", "route", "ls"])

            try:
                gw = [l for l in ip_route_ls_result.stdout.split("\n") if l.startswith("default ")][0].split()[2]
                ping_gw_result = Shell.run(["ping", "-c", "1", "-W", "1", gw])
                ping_gw_report = "\nping gateway (%s): %s" % (gw, print_result(ping_gw_result))
            except:
                ping_gw_report = (
                    "\nUnable to ping gatewy.  " "No gateway could be found in:\n" % ip_route_ls_result.stdout
                )

            if ping_result1.rc != 0:
                time.sleep(30)
                ping_result2 = Shell.run(["ping", "-c", "1", "-W", "1", address])
                ping_result2_report = "\n30s later ping: %s" % print_result(ping_result2)

            msg = (
                "Error connecting to %s: %s.\n"
                "Please add the following to "
                "https://github.com/whamcloud/integrated-manager-for-lustre/issues/%s\n"
                "Performing some diagnostics...\n"
                "ping: %s\n"
                "ifconfig -a: %s\n"
                "ip route ls: %s"
                "%s"
                "%s"
                % (
                    address,
                    e,
                    issue_num,
                    print_result(ping_result1),
                    print_result(ip_addr_result),
                    print_result(ip_route_ls_result),
                    ping_gw_report,
                    ping_result2_report,
                )
            )

            logger.error(msg)

            DEVNULL = open(os.devnull, "wb")
            p = subprocess.Popen(["sendmail", "-t"], stdin=subprocess.PIPE, stdout=DEVNULL, stderr=DEVNULL)
            p.communicate(input=b"To: iml@whamcloud.com\n" b"Subject: GH#%s\n\n" % issue_num + msg)
            p.wait()
            DEVNULL.close()

        logger.debug("remote_command[%s]: %s" % (address, command))
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # the set -e just sets up a fail-safe execution environment where
        # any shell commands in command that fail and are not error checked
        # cause the shell to fail, alerting the caller that one of their
        # commands failed unexpectedly
        command = "set -e; %s" % command

        # exec 0<&- being prefixed to the shell command string below closes
        # the shell's stdin as we don't expect any uses of remote_command()
        # to read from stdin
        if not buffer:
            command = "exec 0<&-; %s" % command

        args = {"username": "root"}
        # If given an ssh_config file, require that it defines
        # a private key and username for accessing this host
        config_path = config.get("ssh_config", None)
        if config_path:
            ssh_config = paramiko.SSHConfig()
            ssh_config.parse(open(config_path))

            host_config = ssh_config.lookup(address)
            address = host_config["hostname"]

            if "user" in host_config:
                args["username"] = host_config["user"]
                if args["username"] != "root" and as_root:
                    command = 'sudo sh -c "{}"'.format(command.replace('"', '\\"'))

            if "identityfile" in host_config:
                args["key_filename"] = host_config["identityfile"][0]

                # Work around paramiko issue 157, failure to parse quoted values
                # (vagrant always quotes IdentityFile)
                args["key_filename"] = args["key_filename"].strip('"')

        logger.info(
            "SSH address = %s, timeout = %d, write len = %d, args = %s" % (address, timeout, len(buffer or ""), args)
        )

        # Create ssh connection
        try:
            ssh.connect(address, **args)
        except paramiko.ssh_exception.SSHException as e:
            host_test(address, "29")
            return Shell.RunResult(1, "", "", timeout=False)

        transport = ssh.get_transport()
        transport.set_keepalive(20)
        channel = transport.open_session()
        channel.settimeout(timeout)

        # Actually execute the command
        try:
            channel.exec_command(command)
        except paramiko.transport.Socket as e:
            host_test(address, "72")
            return Shell.RunResult(1, "", "", timeout=False)

        if buffer:
            stdin = channel.makefile("wb")
            stdin.write(buffer)
            stdin.close()
        # Always shutdown write to ensure executable does not wait on input
        channel.shutdown_write()

        # Store results. This needs to happen in this order. If recv_exit_status is
        # read first, it can block indefinitely due to paramiko bug #448. The read on
        # the stdout will wait until the command finishes, so its not necessary to have
        # recv_exit_status to block on it first. Closing the channel must come last,
        # or else reading from stdout/stderr will return an empty string.
        stdout = channel.makefile("rb").read()
        stderr = channel.makefile_stderr("rb").read()
        rc = channel.recv_exit_status()
        channel.close()

        # Verify we recieved the correct exit status if one was specified.
        if expected_return_code is not None:
            self._test_case.assertEqual(
                rc,
                expected_return_code,
                "rc (%s) != expected_return_code (%s), stdout: '%s', stderr: '%s'"
                % (rc, expected_return_code, stdout, stderr),
            )

        return Shell.RunResult(rc, stdout, stderr, timeout=False)

    def _ssh_fqdn(self, fqdn, command, expected_return_code=0, timeout=TEST_TIMEOUT, buffer=None):
        address = None
        for host in config["lustre_servers"]:
            if host["fqdn"] == fqdn:
                address = host["address"]
        if address is None:
            raise KeyError(fqdn)

        return self._ssh_address(address, command, expected_return_code, timeout, buffer)

    def format_block_device(self, fqdn, path, filesystem_type):
        commands = {
            "ext2": "mkfs.ext2 -F '{path}'".format(path=path),
            "lustre": "mkfs.lustre --mgs '{path}'".format(path=path),
        }
        try:
            command = commands[filesystem_type]
        except KeyError:
            raise RuntimeError("Unknown filesystem type %s (known types are %s)" % (filesystem_type, commands.keys()))

        self._ssh_fqdn(fqdn, command)

    def stop_target(self, fqdn, ha_label):
        return self._ssh_fqdn(fqdn, "chroma-agent stop_target --ha %s" % ha_label)

    def start_target(self, fqdn, ha_label):
        self._ssh_fqdn(fqdn, "chroma-agent start_target --ha %s" % ha_label)

    def import_target(self, fqdn, type, path, pacemaker_ha_operation):
        self._ssh_fqdn(
            fqdn,
            "chroma-agent import_target --device_type %s "
            "--path %s --pacemaker_ha_operation %s" % (type, path, pacemaker_ha_operation),
        )

    def stop_lnet(self, fqdn):
        self._ssh_fqdn(fqdn, "chroma-agent stop_lnet")

    def start_lnet(self, fqdn):
        self._ssh_fqdn(fqdn, "chroma-agent start_lnet")

    def stop_pacemaker(self, fqdn):
        self._ssh_fqdn(fqdn, "chroma-agent stop_pacemaker")

    def start_pacemaker(self, fqdn):
        self._ssh_fqdn(fqdn, "chroma-agent start_pacemaker")

    def stop_corosync(self, fqdn):
        self._ssh_fqdn(fqdn, "chroma-agent stop_corosync")

    def start_corosync(self, fqdn):
        self._ssh_fqdn(fqdn, "chroma-agent start_corosync")

    def restart_chroma_manager(self, fqdn):
        # Do not call this function directly, use restart_chroma_manager in ApiTestCaseWithTestReset class
        self._ssh_address(fqdn, "chroma-config restart")

    def run_iml_diagnostics(self, server, verbose):
        return self._ssh_fqdn(
            server["fqdn"], "iml-diagnostics" + " --all-logs" if verbose else "", timeout=LONG_TEST_TIMEOUT
        )

    def inject_log_message(self, fqdn, message):
        self._ssh_fqdn(fqdn, 'logger "%s"' % message)

    def lctl_get_param(self, address, path):
        result = self._ssh_address(address, "lctl get_param {}".format(path))
        return result.stdout.strip()

    def read_file(self, address, file_path):
        result = self._ssh_address(address, "cat %s" % file_path)
        return result.stdout

    def rename_file(self, address, current_path, new_path):
        # Warning! This will force move by overwriting destination file
        self._ssh_address(address, "mv -f %s %s" % (current_path, new_path))

    def create_file(self, address, file_content, file_path):
        self._ssh_address(address, "echo %s > %s" % (file_content, file_path))

    def delete_file(self, address, file_path):
        self._ssh_address(address, "rm -rf %s" % file_path)

    def copy_file(self, address, current_file_path, new_file_path):
        self._ssh_address(address, "cp %s %s" % (current_file_path, new_file_path))

    def file_exists(self, address, file_path):
        return self._ssh_address(address, "ls %s" % file_path, expected_return_code=None).rc == 0

    def cibadmin(self, server, args, buffer=None):
        # -t 1 == time out after 1 sec. of no response
        cmd = "cibadmin -t 1 %s" % args

        tries = 300
        while tries > 0:
            result = self._ssh_fqdn(server["fqdn"], cmd, expected_return_code=None, buffer=buffer)

            # retry on expected (i.e. waiting for dust to settle, etc.)
            # failures
            if result.rc not in [10, 41, 62, 107]:
                break
            # don't need a sleep here, the cibadmin timeout provides
            # us with a delay
            tries -= 1

        return result

    def backup_cib(self, server):
        backup = "/tmp/cib-backup-%s.xml" % server["nodename"]
        running_targets = self.get_pacemaker_targets(server, running=True)
        for target in running_targets:
            self.stop_target(server["fqdn"], target)

        self._test_case.wait_until_true(lambda: len(self.get_pacemaker_targets(server, running=True)) < 1)

        with open(backup, "w") as f:
            f.write(self.cibadmin(server, "--query").stdout)

        return running_targets

    def restore_cib(self, server, start_targets):
        import xml.etree.ElementTree as xml

        new_cib = xml.fromstring(open("/tmp/cib-backup-%s.xml" % server["nodename"]).read())

        # get the current admin_epoch
        current_cib = xml.fromstring(self.cibadmin(server, "--query").stdout)

        new_cib.set("admin_epoch", str(int(current_cib.get("admin_epoch")) + 1))
        new_cib.set("epoch", "0")

        self.cibadmin(server, "--replace --xml-pipe", buffer=xml.tostring(new_cib))

        for target in start_targets:
            self.start_target(server["fqdn"], target)

        self._test_case.wait_until_true(
            lambda: len(self.get_pacemaker_targets(server, running=True)) == len(start_targets)
        )

    # HYD-2071: These two methods may no longer be useful after the API-side
    # work lands.
    def set_node_standby(self, server):
        self._ssh_address(server["address"], "chroma-agent set_node_standby --node %s" % server["nodename"])

    def set_node_online(self, server):
        self._ssh_address(server["address"], "chroma-agent set_node_online --node %s" % server["nodename"])

    def mount_filesystem(self, client_address, filesystem):
        """
        Mounts a lustre filesystem on a specified client.
        """
        self._ssh_address(client_address, "mkdir -p /mnt/%s" % filesystem["name"])

        self._ssh_address(client_address, filesystem["mount_command"])

        result = self._ssh_address(client_address, "mount")
        self._test_case.assertRegexpMatches(result.stdout, " on /mnt/%s " % filesystem["name"])

    def _unmount_filesystem(self, client, filesystem_name):
        """
        Unmounts a lustre filesystem from the specified client if mounted.
        """
        result = self._ssh_address(client, "mount")
        if re.search(" on /mnt/%s " % filesystem_name, result.stdout):
            logger.debug("Unmounting %s" % filesystem_name)
            self._ssh_address(client, "umount /mnt/%s" % filesystem_name)
        result = self._ssh_address(client, "mount")
        mount_output = result.stdout
        logger.debug("`Mount`: %s" % mount_output)
        self._test_case.assertNotRegexpMatches(mount_output, " on /mnt/%s " % filesystem_name)

    def unmount_filesystem(self, client_address, filesystem):
        """
        Unmounts a lustre filesystem from the specified client if mounted.
        """
        self._unmount_filesystem(client_address, filesystem["name"])

    def check_ha_config(self, hosts, filesystem_name):
        import xml.etree.ElementTree as xml

        def host_has_location(items, test_host):
            for p in items:
                # Pacemaker shifted from nodename to fqdn after el6.
                if socket.getfqdn(p.attrib["node"]) == test_host["fqdn"]:
                    return True

            return False

        def has_primitive(items, fs_name):

            for p in items:
                if os.environ.get("IML_4_INSTALLED", False):
                    if (
                        p.attrib["class"] == "ocf"
                        and p.attrib["provider"] == "chroma"
                        and p.attrib["type"] == "Target"
                        and p.attrib["id"].startswith("{}-".format(fs_name))
                    ):
                        return True
                else:
                    if (
                        p.attrib["id"].startswith("{}-".format(fs_name))
                        and p.attrib["class"] == "ocf"
                        and (
                            (p.attrib["provider"] in ["chroma", "heartbeat"] and p.attrib["type"] == "ZFS")
                            or (p.attrib["provider"] == "lustre" and p.attrib["type"] == "Lustre")
                        )
                    ):
                        return True
            return False

        for host in hosts:
            result = self.cibadmin(host, "--query")
            configuration = xml.fromstring(result.stdout)

            rsc_locations = configuration.findall("./configuration/constraints/rsc_location")
            self._test_case.assertTrue(host_has_location(rsc_locations, host), xml.tostring(configuration))

            primatives = configuration.findall("./configuration/resources//primitive")
            self._test_case.assertTrue(has_primitive(primatives, filesystem_name), xml.tostring(configuration))

    def exercise_filesystem_mdt(self, client_address, filesystem, mdt_index, files_to_create):
        """
        Verify we can actually exercise a filesystem on a specific mdt.

        Currently this only verifies that we can write to a filesystem as a
        sanity check that it was configured correctly.
        """
        # TODO: Expand on entire function. Perhaps use existing lustre client tests.

        if not filesystem.get("bytes_free"):
            self._test_case.wait_until_true(lambda: self._test_case.get_filesystem(filesystem["id"]).get("bytes_free"))
            filesystem = self._test_case.get_filesystem(filesystem["id"])

        bytes_free = filesystem.get("bytes_free")
        assert bytes_free > 0, "Expected bytes_free to be > 0"
        logger.debug("exercise_filesystem: API reports %s has %s bytes free" % (filesystem["name"], bytes_free))

        test_root = "/mnt/%s/mdt%s" % (filesystem["name"], mdt_index)

        if mdt_index:
            self._ssh_address(client_address, "lfs mkdir -i %s %s" % (mdt_index, test_root))
        else:
            self._ssh_address(client_address, "mkdir -p %s" % test_root)

        def actual_exercise(client_address, test_root, file_no, bytes_to_write):
            self._ssh_address(client_address, "mkdir -p %s/%s" % (test_root, file_no))

            self._ssh_address(
                client_address,
                "dd if=/dev/zero of=%s/%s/exercisetest-%s.dat bs=1000 count=%s"
                % (test_root, file_no, file_no, bytes_to_write),
            )

        threads = []

        for file_no in range(0, files_to_create):
            thread = ExceptionThrowingThread(
                target=actual_exercise,
                args=(client_address, test_root, file_no, min((bytes_free * 0.4), 512000) / 1000),
                use_threads=False,
            )
            thread.start()
            threads.append(thread)

        ExceptionThrowingThread.wait_for_threads(
            threads
        )  # This will raise an exception if any of the threads raise an exception

        self._ssh_address(client_address, "rm -rf %s" % test_root)

    def exercise_filesystem(self, client_address, filesystem, mdt_indexes=[0], no_of_files_per_mdt=None):
        """
        Verify we can actually exercise a filesystem.

        Currently this only verifies that we can write to a filesystem as a
        sanity check that it was configured correctly.
        """

        if not no_of_files_per_mdt:
            no_of_files_per_mdt = [10] * len(mdt_indexes)

        threads = []

        for index, mdt_index in enumerate(mdt_indexes):
            thread = ExceptionThrowingThread(
                target=self.exercise_filesystem_mdt,
                args=(client_address, filesystem, mdt_index, no_of_files_per_mdt[index]),
            )

            thread.start()
            threads.append(thread)

        ExceptionThrowingThread.wait_for_threads(
            threads
        )  # This will raise an exception if any of the threads raise an exception

    def _fqdn_to_server_config(self, fqdn):
        for server in config["lustre_servers"]:
            if server["fqdn"] == fqdn:
                return server

        raise RuntimeError("No server config for %s" % fqdn)

    def host_contactable(self, address):
        try:
            # TODO: Better way to check this?
            result = self._ssh_address(
                address, "echo 'Checking if node is ready to receive commands.'", expected_return_code=None
            )

        except socket.error:
            logger.debug("Unknown socket error when checking %s" % address)
            return False
        except paramiko.AuthenticationException as e:
            logger.debug("Auth error when checking %s: %s" % (address, e))
            return False
        except paramiko.SSHException as e:
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
        result = self._ssh_address(address, "cat /proc/uptime")
        secs_up = result.stdout.split()[0]
        return secs_up

    def _host_of_server(self, server):
        return config["hosts"][server["host"]]

    def reset_server(self, fqdn):
        # NB: This is a vaguely dangerous operation -- basically the
        # equivalent of hitting the reset button. It's not a nice
        # shutdown that gives the fs time to sync, etc.
        server_config = self._fqdn_to_server_config(fqdn)
        host = self._host_of_server(server_config)
        reset_cmd = server_config.get("reset_command", None)
        if host.get("reset_is_buggy", False):
            self.kill_server(fqdn)
            self.start_server(fqdn)
        elif reset_cmd:
            result = self._ssh_address(
                server_config["host"], reset_cmd, ssh_key_file=server_config.get("ssh_key_file", None)
            )
            node_status = result.stdout
            if re.search("was reset", node_status):
                logger.info("%s reset successfully" % fqdn)
        else:
            self._ssh_address(
                server_config["address"],
                """
                              echo 1 > /proc/sys/kernel/sysrq;
                              echo b > /proc/sysrq-trigger
                              """,
                expected_return_code=-1,
            )

    def kill_server(self, fqdn):
        # "Pull the plug" on host
        server_config = self._fqdn_to_server_config(fqdn)
        self._ssh_address(
            server_config["host"],
            server_config["destroy_command"],
            as_root=self._host_of_server(server_config).get("virsh_as_root", True),
        )

        i = 0
        last_secs_up = 0
        while self.host_contactable(server_config["address"]):
            # plug a race where the host comes up fast enough to allow ssh to
            # plow through
            secs_up = self.host_up_secs(server_config["address"])
            if secs_up < last_secs_up:
                return

            last_secs_up = secs_up

            i += 1
            time.sleep(1)
            if i > TEST_TIMEOUT:
                raise RuntimeError("Host %s didn't terminate within %s seconds" % (fqdn, TEST_TIMEOUT))

    def start_server(self, fqdn):
        boot_server = self._fqdn_to_server_config(fqdn)

        result = self._ssh_address(
            boot_server["host"],
            boot_server["start_command"],
            as_root=self._host_of_server(boot_server).get("virsh_as_root", True),
        )
        node_status = result.stdout
        if re.search("started", node_status):
            logger.info("%s started successfully" % fqdn)

    def unmount_clients(self):
        """
        Unmount all filesystems of type lustre from all clients in the config.
        """
        for client in config["lustre_clients"]:
            self._ssh_address(client["address"], "umount -t lustre -a")
            self._ssh_address(client["address"], "sed -i '/lustre/d' /etc/fstab")
            if client not in [server["address"] for server in config["lustre_servers"]]:
                # Skip this check if the client is also a server, because
                # both targets and clients look like 'lustre' mounts
                result = self._ssh_address(client["address"], "mount")
                self._test_case.assertNotRegexpMatches(result.stdout, " type lustre")

    def unmount_lustre_targets(self, server):
        """
        Unmount all the lustre targets on the server passed.

        :param server: Target server
        :return: Exception on failure.
        """
        try:
            result = self._ssh_address(server["address"], "umount -t lustre -a")
            logger.info(
                "Unmounting Lustre on %s results... exit code %s.  stdout:\n%s\nstderr:\n%s"
                % (server["nodename"], result.rc, result.stdout, result.stderr)
            )
        except socket.timeout:
            # Uh-oh.  Something bad is happening with Lustre.  Let's see if
            # we can gather some information for the LU team.
            logger.info(
                "Unmounting Lustre on %s timed out.  Going to try to gather debug information." % server["nodename"]
            )
            self._ssh_address(
                server["address"],
                """set -ex
                              echo 1 > /proc/sys/kernel/sysrq
                              echo 8 > /proc/sysrq-trigger
                              echo t > /proc/sysrq-trigger
                              """,
            )
            # going to need to reboot this node to get any use out of it
            self.reset_server(server["fqdn"])
            raise RuntimeError(
                "Timed out unmounting Lustre target(s) on %s.  "
                "Debug data has been collected.  "
                "Make sure to add it to an existing ticket or "
                "create a new one." % server["nodename"]
            )
        if result.rc != 0:
            logger.info(
                "Unmounting Lustre on %s failed with exit code %s.  stdout:\n%s\nstderr:\n%s"
                % (server["nodename"], result.rc, result.stdout, result.stderr)
            )
            raise RuntimeError(
                "Failed to unmount lustre on '%s'!\nrc: %s\nstdout: %s\nstderr: %s"
                % (server, result.rc, result.stdout, result.stderr)
            )

    def is_worker(self, server):
        workers = [w["address"] for w in config["lustre_servers"] if "worker" in w.get("profile", "")]
        return server["address"] in workers

    @property
    def config_workers(self):
        return [w for w in config["lustre_servers"] if self.is_worker(w)]

    def has_pacemaker(self, server):
        result = self._ssh_address(server["address"], "which crmadmin", expected_return_code=None)
        return result.rc == 0

    def get_pacemaker_targets(self, server, running=False):
        """
        Returns a list of chroma targets configured in pacemaker on a server.
        :param running: Restrict the returned list only to running targets.
        """
        result = self._ssh_address(server["address"], "crm_resource -L")
        crm_resources = result.stdout.split("\n")
        targets = []
        for r in crm_resources:
            if not re.search("lustre:Lustre", r):
                continue

            target = r.split()[0]
            if running and re.search("Started\s*$", r):
                targets.append(target)
            elif not running:
                targets.append(target)
        return targets

    def is_pacemaker_target_running(self, server, target):
        result = self._ssh_address(server["address"], "crm_resource -r %s -W" % target)
        return re.search("is running", result.stdout)

    def get_fence_nodes_list(self, address, ignore_failure=False):
        result = self._ssh_address(address, "fence_chroma -o list", expected_return_code=None if ignore_failure else 0)

        if result.rc != 0:
            logger.debug("fence_chroma stderr: %s" % result.stderr)
            return []

        # -o list returns:
        # host1,\n
        # host2,\n
        # ...
        # List is fqdns on el7, short names on el6, normalised to always contain fqdns
        return [socket.getfqdn(node) for node in result.stdout.split(",\n") if node]

    def remove_config(self, server_list):
        """
        Remove /etc/chroma.cfg on the test servers.
        """
        for server in server_list:
            self._ssh_address(server["address"], "rm -f /etc/chroma.cfg")

    def write_config(self, server_list):
        """
        Write out /etc/chroma.cfg on the test servers.
        """
        from ConfigParser import SafeConfigParser
        from StringIO import StringIO

        sections = ["corosync"]

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
                self._ssh_address(server["address"], "cat > /etc/chroma.cfg", buffer=cfg_str.getvalue())

        self.sync_disks([s["address"] for s in server_list])

    def sync_disks(self, server_list):
        """
        Runs a 'sync' on the targeted server(s) to ensure that caches
        are flushed. Usually not necessary, but can help to avoid races
        between configs getting to disk and powercycle operations.
        """
        for server in server_list:
            self._ssh_address(server, "sync; sync")

    def has_chroma_agent(self, server):
        result = self._ssh_address(server, "which chroma-agent", expected_return_code=None)
        return result.rc == 0

    def stop_agents(self, server_list):
        for server in server_list:
            if self.has_chroma_agent(server):
                self._ssh_address(server, stop_agent_cmd)

    def start_agents(self, server_list):
        for server in server_list:
            self._ssh_address(server, "systemctl start iml-storage-server.target")

    def catalog_rpms(self, server_list, location, sorted=False):
        """
        Runs an 'rpm -qa' on the targeted server(s) redirecting the
        output into the named file, optionally piped through sort
        """
        sort_cmd = ""
        if sorted:
            sort_cmd = " | sort"
        for server in server_list:
            self._ssh_address(server, "rpm -qa %s > %s" % (sort_cmd, location))

    def clear_ha(self, server_list):
        """
        Stops and deletes all chroma targets for any corosync clusters
        configured on any of the lustre servers appearing in the cluster config
        """
        for server in server_list:
            address = server["address"]

            if self.is_worker(server):
                logger.info("{} is configured as a worker -- skipping.".format(address))
                continue

            if not self.has_pacemaker(server):
                logger.info("{} does not appear to have pacemaker - skipping any removal of targets.".format(address))
                continue

            firewall = RemoteFirewallControl.create(address, self._ssh_address_no_check)

            result = self._ssh_address(
                address,
                "if crm_mon -b1; then crm_attribute --type crm_config --name maintenance-mode --update true; fi",
            )
            logger.debug("CMD OUTPUT:\n%s" % result.stdout)

            result = self._ssh_address(
                address,
                "if crm_mon -b1; then crm_resource -l | xargs -n 1 crm_resource --set-parameter target-role --meta --parameter-value Stopped --resource; fi",
            )
            logger.debug("CMD OUTPUT:\n%s" % result.stdout)

            result = self._ssh_address(
                address,
                "if crm_mon -b1; then crm_attribute --type crm_config --name maintenance-mode --delete true; fi",
            )

            logger.debug("CMD OUTPUT:\n%s" % result.stdout)

            result = self._ssh_address(address, "if crm_mon -b1; then pcs cluster stop --all; fi")
            logger.debug("CMD OUTPUT:\n%s" % result.stdout)

            result = self._ssh_address(address, "pcs cluster destroy")
            logger.debug("CMD OUTPUT:\n%s" % result.stdout)

            self._ssh_address(address, "systemctl disable --now pcsd pacemaker corosync")

            self._ssh_address(address, "ifconfig %s 0.0.0.0 down" % (server["corosync_config"]["ring1_iface"]))
            self._ssh_address(
                address,
                "rm -f /etc/sysconfig/network-scripts/ifcfg-%s /etc/corosync/corosync.conf /var/lib/pacemaker/cib/* /var/lib/corosync/*"
                % (server["corosync_config"]["ring1_iface"]),
            )

            self._ssh_address(address, firewall.remote_add_port_cmd(22, "tcp"))
            self._ssh_address(address, firewall.remote_add_port_cmd(988, "tcp"))

    def clear_lnet_config(self, server_list):
        """
        Removes the lnet configuration file for the server list passed.
        """

        for server in server_list:
            self._ssh_address(
                server["address"],
                """
                              [ -f /etc/modprobe.d/iml_lnet_module_parameters.conf ] &&
                              rm -f /etc/modprobe.d/iml_lnet_module_parameters.conf &&
                              lustre_rmmod
                              """,
                expected_return_code=None,
            )  # Keep going if it failed - may be none there.

    def install_upgrades(self):
        raise NotImplementedError("Automated test of upgrades is HYD-1739")

    def scan_packages(self, fqdn):
        raise NotImplementedError()

    def get_package_version(self, fqdn, package):
        raise NotImplementedError("Automated test of upgrades is HYD-1739")

    def get_corosync_port(self, fqdn):
        mcast_port = None
        for line in self._ssh_address(fqdn, "cat /etc/corosync/corosync.conf || true").stdout.split("\n"):
            match = re.match("\s*mcastport:\s*(\d+)", line)
            if match:
                mcast_port = match.group(1)
                break

        return int(mcast_port) if mcast_port is not None else None

    def grep_file(self, server, string, file):
        result = self._ssh_address(server["address"], 'grep -e "%s" %s || true' % (string, file)).stdout
        return result

    def get_file_content(self, server, file):
        result = self._ssh_address(server["address"], 'cat "%s" || true' % file).stdout
        return result

    def enable_agent_debug(self, server_list):
        for server in server_list:
            self._ssh_address(server["address"], "touch /tmp/chroma-agent-debug")

    def disable_agent_debug(self, server_list):
        for server in server_list:
            self._ssh_address(server["address"], "rm -f /tmp/chroma-agent-debug")

    def omping(self, server, servers, count=5, timeout=30):
        firewall = RemoteFirewallControl.create(server["address"], self._ssh_address_no_check)

        self._ssh_address(server["address"], firewall.remote_add_port_cmd(4321, "udp"))

        result = self._ssh_address(
            server["address"],
            "exec 2>&1; omping -T %s -c %s %s" % (timeout, count, " ".join([s["nodename"] for s in servers])),
        )

        self._ssh_address(server["address"], firewall.remote_remove_port_cmd(4321, "udp"))

        return result.stdout

    def yum_update(self, server):
        self._ssh_address(server["address"], "yum -y update")

    def yum_upgrade_exclude_python2_iml(self, server):
        self._ssh_address(server["address"], "yum -y upgrade --exclude=python2-iml*")

    def yum_check_update(self, server):
        available_updates = self._ssh_address(
            server["address"], "yum check-update | xargs -n3 | column -t | awk '{print$1}'"
        )
        available_updates = filter(
            lambda x: x != "Loaded" and x != "Loading" and x != "from" and x != "*",
            available_updates.stdout.split("\n"),
        )
        logger.debug("yum_check_update results: {}".format(available_updates))
        return available_updates

    def default_boot_kernel_path(self, server):
        r = self._ssh_address(server["address"], "grubby --default-kernel")
        stdout = r.stdout.rstrip()

        return stdout

    def get_chroma_repos(self):
        result = self._ssh_address(config["chroma_managers"][0]["address"], "ls /var/lib/chroma/repo/")
        return result.stdout.split()

    def check_time_within_range(self, first_dt, second_dt, minutes):
        """check if first_dt datetime value is within 'minutes' of the second_dt"""
        min_dt = second_dt - datetime.timedelta(minutes=minutes)
        max_dt = second_dt + datetime.timedelta(minutes=minutes)

        return min_dt < first_dt < max_dt

    def get_server_time(self, client_address):
        """return datetime.datetime from UTC date on client"""
        _date_get_format = "%Y:%m:%d:%H:%M"

        time_string = self._ssh_address(client_address, "date -u +%s" % _date_get_format).stdout.strip("\n")

        # create datetime.datetime from linux date utility shell output
        return datetime.datetime(*[int(element) for element in time_string.split(":")])

    def set_server_time(self, client_address, new_datetime):
        """set client date & time with date utility, use utility defined format"""
        _date_set_format = "%Y%m%d %H:%M"

        time_string = new_datetime.strftime(_date_set_format)
        result = self._ssh_address(client_address, 'date -u --set="%s"' % time_string)

        return result
