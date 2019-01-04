# -*- coding: utf-8 -*-
# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

from paramiko import SSHException, AuthenticationException
import socket
import subprocess
import urlparse
import traceback
import sys
import random

from django.db import models

from chroma_core.models.jobs import Job
from chroma_core.lib.job import Step
from chroma_help.help import help_text
from chroma_core.lib.job import job_log
from iml_common.lib.name_value_list import NameValueList

import settings


# Store credentials here, we do not want them to be in the database.
# We delete them when we have finished with them.
credentials_table = {}


class TestHostConnectionStep(Step):
    def _test_hostname(self, agent_ssh, auth_args, address, resolved_address):
        from chroma_core.services.job_scheduler.agent_rpc import AgentException

        try:
            # Check that the system hostname:
            # a) resolves
            # b) does not resolve to a loopback address
            rc, out, err = self._try_ssh_cmd(
                agent_ssh, auth_args, "python -c 'import socket; print socket.gethostbyname(socket.gethostname())'"
            )
            hostname_resolution = out.rstrip()
        except AgentException:
            job_log.exception("Exception thrown while trying to invoke agent on '%s':" % address)
        else:
            if rc != 0:
                job_log.error("Failed configuration check on '%s': hostname does not resolve (%s)" % (address, err))
                return False, False, False
            if hostname_resolution.startswith("127"):
                job_log.error(
                    "Failed configuration check on '%s': hostname resolves to a loopback address (%s)"
                    % (address, hostname_resolution)
                )
                return False, False, False

        try:
            rc, out, err = self._try_ssh_cmd(agent_ssh, auth_args, "python -c 'import socket; print socket.getfqdn()'")
            assert rc == 0, "failed to get fqdn on %s: %s" % (address, err)
            fqdn = out.rstrip()
        except (AssertionError, AgentException):
            job_log.exception("Exception thrown while trying to invoke agent on '%s':" % address)
            return False, False, False

        try:
            resolved_fqdn = socket.gethostbyname(fqdn)
        except socket.gaierror:
            job_log.error("Failed configuration check on '%s': can't resolve self-reported fqdn '%s'" % (address, fqdn))
            return True, False, False

        if resolved_fqdn != resolved_address:
            job_log.error(
                "Failed configuration check on '%s': self-reported fqdn resolution '%s' doesn't match address resolution"
                % (address, fqdn)
            )
            return True, True, False

        # Everything's OK (we hope!)
        return True, True, True

    def _test_reverse_ping(self, agent_ssh, auth_args, address, manager_hostname):
        from chroma_core.services.job_scheduler.agent_rpc import AgentException

        try:
            # Test resolution/ping from server back to manager
            rc, out, err = self._try_ssh_cmd(agent_ssh, auth_args, "ping -c 1 %s" % manager_hostname)
        except AgentException:
            job_log.exception("Exception thrown while trying to invoke agent on '%s':" % address)
            return False, False

        if rc == 0:
            # Can resolve, can ping
            return True, True
        elif rc == 1:
            # Can resolve, cannot ping
            job_log.error("Failed configuration check on '%s': Can't ping %s" % (address, manager_hostname))
            return True, False
        else:
            # Cannot resolve, cannot ping
            job_log.error("Failed configuration check on '%s': Can't resolve %s" % (address, manager_hostname))
            return False, False

    def _test_yum_sanity(self, agent_ssh, auth_args, address):
        from chroma_core.services.job_scheduler.agent_rpc import AgentException

        can_update = False

        try:
            # Check to see if yum can or ever has gotten OS repo metadata
            check_yum = """
python -c "from yum import YumBase
yb = YumBase()
missing_electric_fence = not [p.name for p in yb.pkgSack.returnNewestByNameArch() if p.name == 'ElectricFence']
exit(missing_electric_fence)"
"""
            rc, out, err = self._try_ssh_cmd(agent_ssh, auth_args, check_yum)
            if rc == 0:
                can_update = True
            else:
                job_log.error("Failed configuration check on '%s': Unable to access any yum mirrors" % address)
        except AgentException:
            job_log.exception("Exception thrown while trying to invoke agent on '%s':" % address)
            return False, False

        return can_update

    def _test_openssl(self, agent_ssh, auth_args, address):
        from chroma_core.services.job_scheduler.agent_rpc import AgentException

        try:
            rc, out, err = self._try_ssh_cmd(agent_ssh, auth_args, "openssl version -a")
        except AgentException:
            job_log.exception("Exception thrown while trying to invoke agent on '%s':" % address)
            return False
        return not rc

    def _try_ssh_cmd(self, agent_ssh, auth_args, cmd):
        from chroma_core.services.job_scheduler.agent_rpc import AgentException

        try:
            return agent_ssh.ssh(cmd, auth_args=auth_args)
        except (AuthenticationException, SSHException):
            raise
        except Exception as e:
            # Re-raise wrapped in an AgentException
            raise AgentException(
                agent_ssh.address,
                "Unhandled exception: %s" % e,
                ", ".join(auth_args),
                "\n".join(traceback.format_exception(*(sys.exc_info()))),
            )

    def is_dempotent(self):
        return True

    def run(self, kwargs):
        """Test that a host at this address can be created

        See create_host_ssh for explanation of parameters

        TODO: Break this method up, normalize the checks

        Use threaded timeouts on possible long running commands.  The idea is
        that if the command takes longer than the timeout, you might get a
        false negative - the command didn't fail, we just cut it short.
        Not sure this is an issue in practice, so going to stop here no ticket.
        """
        from chroma_core.services.job_scheduler.agent_rpc import AgentSsh

        credentials = credentials_table[kwargs["credentials_key"]]
        del credentials_table[kwargs["credentials_key"]]

        address = kwargs["address"]
        root_pw = credentials["root_pw"]
        pkey = credentials["pkey"]
        pkey_pw = credentials["pkey_pw"]

        agent_ssh = AgentSsh(address, timeout=5)
        user, hostname, port = agent_ssh.ssh_params()

        auth_args = agent_ssh.construct_ssh_auth_args(root_pw, pkey, pkey_pw)

        try:
            resolved_address = socket.gethostbyname(hostname)
        except socket.gaierror:
            resolve = False
            ping = False
        else:
            resolve = True
            ping = 0 == subprocess.call(["ping", "-c 1", resolved_address])

        manager_hostname = urlparse.urlparse(settings.SERVER_HTTP_URL).hostname

        status = NameValueList(
            [
                {"resolve": resolve},
                {"ping": ping},
                {"auth": False},
                {"hostname_valid": False},
                {"fqdn_resolves": False},
                {"fqdn_matches": False},
                {"reverse_resolve": False},
                {"reverse_ping": False},
                {"yum_can_update": False},
                {"openssl": False},
            ]
        )

        if resolve and ping:
            try:
                status["reverse_resolve"], status["reverse_ping"] = self._test_reverse_ping(
                    agent_ssh, auth_args, address, manager_hostname
                )
                status["hostname_valid"], status["fqdn_resolves"], status["fqdn_matches"] = self._test_hostname(
                    agent_ssh, auth_args, address, resolved_address
                )
                status["yum_can_update"] = self._test_yum_sanity(agent_ssh, auth_args, address)
                status["openssl"] = self._test_openssl(agent_ssh, auth_args, address)
            except (AuthenticationException, SSHException):
                #  No auth methods available, or wrong credentials
                status["auth"] = False
            else:
                status["auth"] = True

        return {
            "address": address,
            "valid": all(entry.value is True for entry in status),
            "status": status.collection(),
        }


class TestHostConnectionJob(Job):
    address = models.CharField(max_length=256)
    credentials_key = models.IntegerField()

    # We want to remove the credentials because we don't want them in memory
    def __init__(self, *args, **kwargs):
        # When reading a record there are no kwargs, we are only fiddling in the creation state.
        if "root_pw" in kwargs:
            # Turn the random into an int so we don't get any rounding errors down the road.
            kwargs["credentials_key"] = int(random.random() * 2147483647)

            credentials = {"root_pw": kwargs["root_pw"], "pkey": kwargs["pkey"], "pkey_pw": kwargs["pkey_pw"]}

            del kwargs["root_pw"]
            del kwargs["pkey"]
            del kwargs["pkey_pw"]

            super(TestHostConnectionJob, self).__init__(*args, **kwargs)

            credentials_table[self.credentials_key] = credentials
        else:
            super(TestHostConnectionJob, self).__init__(*args, **kwargs)

    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    @classmethod
    def long_description(cls, stateful_object):
        return help_text["test_for_host_connectivity"]

    def description(self):
        return "Test for host connectivity"

    def get_steps(self):
        return [(TestHostConnectionStep, {"address": self.address, "credentials_key": self.credentials_key})]
