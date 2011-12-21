
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

import json
import time
import pickle


class AgentException(Exception):
    def __init__(self, host_id = None, cmdline = None, agent_exception = None, agent_backtrace = None):
        # NB we accept construction without arguments in order to be picklable
        self.host_id = host_id
        self.cmdline = cmdline
        self.agent_exception = agent_exception
        self.agent_backtrace = agent_backtrace

    def __str__(self):
        from configure.models import ManagedHost
        return """AgentException
Host: %s
Command: %s
Exception: %s (%s)
%s
""" % (ManagedHost.objects.get(pk = self.host_id),
        self.cmdline,
        self.agent_exception,
        self.agent_exception.__class__.__name__,
        self.agent_backtrace)


class Agent(object):
    def __init__(self, host, log = None, console_callback = None, timeout = None):

        # Long default timeout for long-running jobs like formatting a lun
        DEFAULT_TIMEOUT = 3600
        if timeout:
            self.timeout = timeout
        else:
            self.timeout = DEFAULT_TIMEOUT

        self.host = host

        self.console_callback = console_callback

        if log:
            self.log = log
        else:
            import logging
            self.log = logging.getLogger(None)

    def console_append(self, chunk):
        if self.console_callback:
            self.console_callback(chunk)

    def _ssh(self, command):
        import paramiko
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # How long it may take to establish a TCP connection
        SOCKET_TIMEOUT = self.timeout
        # How long it may take to get the output of our agent
        # (including eg tunefs'ing N devices)
        SSH_READ_TIMEOUT = self.timeout

        user, hostname, port = self.host.ssh_params()

        args = {"username": user,
                "timeout": SOCKET_TIMEOUT}
        if port:
            args["port"] = int(port)
        # Note: paramiko has a hardcoded 15 second timeout on SSH handshake after
        # successful TCP connection (Transport.banner_timeout).
        ssh.connect(hostname, **args)
        transport = ssh.get_transport()
        transport.set_keepalive(20)
        channel = transport.open_session()
        channel.settimeout(SSH_READ_TIMEOUT)

        header = "====\nSSH %s\nCommand: '%s'\n====\n\n" % (self.host, command)
        self.console_append(header)

        channel.exec_command(command)

        stderr_buf = ""
        stdout_buf = ""
        while (not channel.exit_status_ready()) or channel.recv_ready() or channel.recv_stderr_ready():
            while channel.recv_ready():
                chunk = channel.recv(4096)
                stdout_buf = stdout_buf + chunk
            while channel.recv_stderr_ready():
                chunk = channel.recv_stderr(4096)
                stderr_buf = stderr_buf + chunk
                self.console_append(chunk)

            time.sleep(0.1)

        result_code = channel.recv_exit_status()

        ssh.close()

        self.log.debug("_ssh:%s:%s:%s" % (self.host, result_code, command))
        if result_code != 0:
            self.log.error("_ssh: nonzero rc %d" % result_code)
            self.log.error(stdout_buf)
            self.log.error(stderr_buf)
        return result_code, stdout_buf, stderr_buf

    def invoke(self, cmd, args = None):
        args_str = ""
        if args:
            from re import escape
            args_str = "--args %s" % escape(json.dumps(args))
        cmdline = "hydra-agent.py %s %s" % (cmd, args_str)
        code, out, err = self._ssh(cmdline)

        if code == 0:
            # May raise a ValueError
            try:
                data = json.loads(out)
            except ValueError:
                raise RuntimeError("Malformed JSON from agent on host %s" % self.host)

            try:
                if data['success']:
                    return data['result']
                else:
                    exception = pickle.loads(data['exception'])
                    backtrace = data['backtrace']
                    self.log.error("Agent returned exception from host %s running '%s': %s" % (self.host, cmdline, backtrace))
                    raise AgentException(self.host.id, cmdline, exception, backtrace)
            except KeyError, e:
                raise RuntimeError("Malformed output (%s) from agent: '%s'" % (e, out))

        else:
            raise RuntimeError("Error running agent on %s" % (self.host))
