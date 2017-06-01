# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import glob
import json
import threading
import sys
import socket
import SocketServer
import time
from cluster_sim.utils import Persisted
from cluster_sim.log import log
from chroma_agent.agent_client import ExceptionCatchingThread

ESC = [chr(27)]
# http://support.microsoft.com/kb/231866
# In reality, ctrl-c is being transformed into:
# IP (Suspend), DO TIMING_MARK
CTRL_C = [chr(255), chr(244), chr(255), chr(253), chr(6)]
# Apparently OS X telnet is different? Sends EOF.
EOF = [chr(255), chr(236)]
# ... To which we respond: NOPE, WON'T DO IT, which is sufficient to
# make the client go about its business.
# http://tools.ietf.org/html/rfc860
WONT_TIMING_MARK = [chr(255), chr(252), chr(6)]

# 23xx looks pretty clear on OS X
BASE_PDU_SERVER_PORT = 2300
PDU_SERVER_ADDRESS = '127.0.0.1'

# on a real PDU, there is a brief pause between off and on when cycled
OUTLET_CYCLE_TIME = 3


class PDUSimulatorTcpHandler(SocketServer.BaseRequestHandler):
    def handle(self):
        log.debug("Handling PDU request from %s:%s" % self.client_address)
        self.server.pdu_simulator.handle_client(self.request,
                                                self.client_address)


class PDUSimulatorTcpServer(SocketServer.TCPServer):
    def __init__(self, *args, **kwargs):
        self.pdu_simulator = kwargs.pop('pdu_simulator')
        # Allow the address to be re-used, otherwise we may get stuck in
        # a TIME_WAIT timeout if there wasn't a clean connection teardown.
        SocketServer.TCPServer.allow_reuse_address = True
        # SocketServer classes are not new-style classes.
        SocketServer.TCPServer.__init__(self, *args, **kwargs)


class PDUSimulatorServer(ExceptionCatchingThread):
    def __init__(self, pdu):
        log.info("Creating PDU server for %s on %s:%s" %
                 (pdu.name, pdu.address, pdu.port))

        self.server = PDUSimulatorTcpServer((pdu.address, pdu.port),
                                            PDUSimulatorTcpHandler,
                                            pdu_simulator = pdu)

        super(PDUSimulatorServer, self).__init__()

    def stop(self):
        self.server.shutdown()

    def _run(self):
        self.server.serve_forever()
        self.server.server_close()


class PDUSimulator(Persisted):
    default_state = {
        'outlets': {}
    }

    def __init__(self, folder, address, port, pdu_name, outlets, poweroff_hook=None, poweron_hook=None):
        self.address = address
        self.port = port
        self.name = pdu_name
        self.poweroff_hook = poweroff_hook
        self.poweron_hook = poweron_hook
        super(PDUSimulator, self).__init__(folder)

        self._lock = threading.Lock()

        self.state['klass'] = self.__class__.__name__
        self.state['name'] = pdu_name
        self.state['outlets'] = outlets
        self.state['address'] = address
        self.state['port'] = port
        self.save()

    def add_outlet(self, outlet):
        with self._lock:
            self.state['outlets'][outlet] = True
            self.save()

    def handle_client(self, sock, address):
        log.info("%s: received connection from %s:%s" % (self.__class__.__name__,
                                                         address[0], address[1]))
        fd = sock.makefile()
        fd.write("NOT IMPLEMENTED\r\n")
        fd.flush()
        sock.close()

    @property
    def filename(self):
        return "pdu_sim_%s.json" % self.name

    def outlet_is_on(self, outlet):
        with self._lock:
            return self.state['outlets'][outlet]

    def outlet_state(self, outlet):
        if not self._lock.locked():
            with self._lock:
                state = self.state['outlets'][outlet]
        else:
            state = self.state['outlets'][outlet]

        return "ON" if state else "OFF"

    @property
    def all_outlet_states(self):
        with self._lock:
            return dict([[o, self.outlet_state(o)] for o in self.state['outlets'].keys()])

    def toggle_outlet(self, outlet, state):
        with self._lock:
            self.state['outlets'][outlet] = state
            log.info("POWER: Toggled %s:%s to %s" % (self.name, outlet,
                                                     self.outlet_state(outlet)))
            self.save()

    def set_outlet_on(self, outlet):
        self.toggle_outlet(outlet, True)

        if self.poweron_hook:
            self.poweron_hook(outlet)

    def set_outlet_off(self, outlet):
        self.toggle_outlet(outlet, False)

        if self.poweroff_hook:
            self.poweroff_hook(outlet)

    def cycle_outlet(self, outlet):
        self.set_outlet_off(outlet)
        time.sleep(OUTLET_CYCLE_TIME)
        self.set_outlet_on(outlet)


class APC79xxSimulator(PDUSimulator):
    def handle_client(self, sock, address):
        log.info("%s: received connection from %s:%s" % (self.__class__.__name__,
                                                         address[0], address[1]))
        self.client_address = address
        self.socket = sock
        self.fd = sock.makefile()

        try:
            self.login()
        except socket.error:
            log.info("%s: client %s:%s disconnected" % (self.__class__.__name__,
                                                        address[0], address[1]))

    def navigation_prompt(self, prompt, forward_choices, forward, backward, banner=None):
        if hasattr(forward_choices, 'split'):
            forward_choices = forward_choices.split()

        lead_prompt = prompt
        if banner:
            lead_prompt = "%s%s" % (banner, prompt)
        self.fd.write("\r\n%s" % lead_prompt)
        self.fd.flush()
        recv_buf = []
        while True:
            response = ""
            while True:
                # This was not my first choice, but it turns out that
                # we have to interpret telnet control sequences in order
                # to accommodate real fence agents.  Sigh.
                c = self.socket.recv(1)
                if c in "\r\n":
                    response = "".join(recv_buf)
                    del(recv_buf[:])
                    # Eat the LF
                    c = self.socket.recv(1)
                    break
                recv_buf.append(c)

                if recv_buf == CTRL_C:
                    for c in WONT_TIMING_MARK:
                        self.socket.send(c)
                    self.control_console()
                elif recv_buf == EOF:
                    self.logout()
                elif recv_buf == ESC:
                    backward(self.last_choice)

            if response in forward_choices:
                self.last_choice = response
                forward(response)
            elif response == "":
                self.fd.write("\r\n%s" % prompt)
                self.fd.flush()
            else:
                # i know it's a hack, so sue me.
                if forward == self.device_manager and response == "4":
                    self.logout()
                else:
                    import inspect
                    caller = inspect.stack()[1][3]

                    decoded_response = [ord(c) for c in response]
                    log.error("Unhandled response in %s: '%s' (%s)" %
                              (caller, response, decoded_response))

                    self.fd.write("\r\n%s" % prompt)
                    self.fd.flush()

    def _strip_controls(self, string):
        cleaned = []
        seen_enq = False
        for c in string:
            if c == chr(5):
                seen_enq = True
                continue

            if not seen_enq:
                continue
            else:
                cleaned.append(c)
        return "".join(cleaned)

    def login(self):
        self.fd.write("\n\rUser Name : ")
        self.fd.flush()
        # We don't really need to do this, but it's nice to get rid of the
        # telnet control characters for logging.
        username = self._strip_controls(self.fd.readline().rstrip())
        self.fd.readline()
        log.debug("Received username: %s" % username)
        self.fd.write("\rPassword : ")
        self.fd.flush()
        password = self.fd.readline().rstrip()
        self.fd.readline()
        log.debug("Received password: %s" % password)
        self.control_console()

    def control_console(self, *args):
        banner = """\n\n
American Power Conversion               Network Management Card AOS      v3.7.3
(c) Copyright 2009 All Rights Reserved  Rack PDU APP                     v3.7.3
-------------------------------------------------------------------------------
Name      : RackPDU                                   Date : 02/13/2013
Contact   : Unknown                                   Time : 10:49:37
Location  : Unknown                                   User : Administrator
Up Time   : 7 Days 15 Hours 31 Minutes                Stat : P+ N+ A+

Switched Rack PDU: Communication Established
"""
        prompt = """
------- Control Console -------------------------------------------------------

     1- Device Manager
     2- Network
     3- System
     4- Logout

     <ESC>- Main Menu, <ENTER>- Refresh, <CTRL-L>- Event Log
> """
        self.navigation_prompt(prompt, "1", self.device_manager,
                               self.control_console, banner)

    def device_manager(self, *args):
        prompt = """
------- Device Manager --------------------------------------------------------

     1- Phase Management
     2- Outlet Management
     3- Power Supply Status

     <ESC>- Back, <ENTER>- Refresh, <CTRL-L>- Event Log
> """

        self.navigation_prompt(prompt, "2", self.outlet_manager,
                               self.control_console)

    def outlet_manager(self, *args):
        prompt = """
------- Outlet Management -----------------------------------------------------

     1- Outlet Control/Configuration
     2- Outlet Restriction

     <ESC>- Back, <ENTER>- Refresh, <CTRL-L>- Event Log
> """

        self.navigation_prompt(prompt, "1", self.outlet_control,
                               self.device_manager)

    @property
    def outlet_status_string(self):
        status_strings = []
        for outlet in sorted(self.state['outlets']):
            status_strings.append("     %s- Outlet %s                 %s" % (outlet, outlet, self.outlet_state(outlet)))
        return "\r\n".join(status_strings)

    def outlet_control(self, *args):
        prompt = """
------- Outlet Control/Configuration ------------------------------------------
%s\r

     <ESC>- Back, <ENTER>- Refresh, <CTRL-L>- Event Log
> """ % self.outlet_status_string
        outlet_choices = self.state['outlets'].keys()

        self.navigation_prompt(prompt, outlet_choices, self.display_outlet,
                               self.outlet_manager)

    def display_outlet(self, number):
        prompt = """
------- Outlet %s -------------------------------------------------------------

        Name         : Outlet %s
        Outlet       : %s
        State        : %s

     1- Control Outlet
     2- Configure Outlet

     ?- Help, <ESC>- Back, <ENTER>- Refresh, <CTRL-L>- Event Log
> """ % (number, number, number, self.outlet_state(number))

        self.current_outlet = number
        self.navigation_prompt(prompt, "1", self.control_outlet,
                               self.outlet_control)

    def control_outlet(self, number):
        prompt = """
------- Control Outlet --------------------------------------------------------

        Name         : Outlet %s
        Outlet       : %s
        State        : %s

     1- Immediate On
     2- Immediate Off
     3- Immediate Reboot
     4- Delayed On
     5- Delayed Off
     6- Delayed Reboot
     7- Cancel

     ?- Help, <ESC>- Back, <ENTER>- Refresh, <CTRL-L>- Event Log
> """ % (self.current_outlet, self.current_outlet, self.outlet_state(self.current_outlet))

        choices = [str(c) for c in range(1, 7)]
        self.navigation_prompt(prompt, choices, self.switch_outlet,
                               self.display_outlet)

    def switch_outlet(self, choice):
        prompt = """
        -----------------------------------------------------------------------
        I'm too lazy to go through all the various permutations.
        The key line expected by fence_apc is the next one:

        Enter 'YES' to continue or <ENTER> to cancel : """

        padding = "        "

        commands = {
            "1": self.set_outlet_on,
            "2": self.set_outlet_off,
            "3": self.cycle_outlet,
            "4": self.set_outlet_on,
            "5": self.set_outlet_off,
            "6": self.cycle_outlet
        }

        self.fd.write("%s" % prompt)
        self.fd.flush()
        response = self.fd.readline().rstrip()
        self.fd.readline()
        if response == "YES":
            commands[choice](self.current_outlet)
            self.fd.write("%sCommand successfully issued.\r\n" % padding)
            self.fd.flush()

        self.fd.write("\r\n%sPress <ENTER> to continue...\r\n" % padding)
        self.fd.flush()

        self.last_choice = self.current_outlet
        self.control_outlet(self.current_outlet)

    def logout(self):
        self.fd.write("Connection Closed - Bye\r\n")
        self.fd.flush()
        log.info("Client %s:%s logged out" % self.client_address)
        self.fd.close()
        self.socket.close()


class APC79xxSimulatorClient(object):
    def __init__(self, address, port):
        self.address = address
        self.port = port

    def perform_outlet_action(self, outlet, action):
        log.debug("%s: Running %s -> %s on %s:%s" %
                  (self.__class__.__name__, outlet, action, self.address, self.port))
        actions = {
            "on": "1",
            "off": "2",
            "reboot": "3"
        }
        # Quick and dirty
        sock = socket.create_connection((self.address, self.port))
        sock.recv(4096)
        sock.send("%s%s%sfoo\n\n" % (chr(255), chr(253), chr(5)))
        sock.recv(4096)
        sock.send("bar\n\n")
        sock.recv(4096)
        sock.send("1\n\n")
        sock.recv(4096)
        sock.send("2\n\n")
        sock.recv(4096)
        sock.send("1\n\n")
        sock.recv(4096)
        sock.send("%s\n\n" % outlet)
        sock.recv(4096)
        sock.send("1\n\n")
        sock.recv(4096)
        sock.send("%s\n\n" % actions[action])
        sock.recv(4096)
        sock.send("YES\n\n")
        sock.recv(4096)
        sock.send("\n\n")
        sock.recv(4096)
        sock.send("".join(CTRL_C))
        sock.close()


class FakePowerControl(Persisted):
    filename = 'fake_power_control.json'
    default_state = {
        'server_outlets': {},
        'outlet_servers': {}
    }

    def _load_pdu_sims(self):
        for pdu_conf in glob.glob("%s/pdu_sim_*.json" % self.folder):
            conf = json.load(open(pdu_conf))
            # assumes all sim classes are in this module...
            klass = getattr(sys.modules[self.__class__.__module__], conf['klass'])
            self.pdu_sims[conf['name']] = klass(self.folder, conf['address'], conf['port'], conf['name'], conf['outlets'], self.server_poweroff_hook, self.server_poweron_hook)

    def __init__(self, path, start_server_fn, stop_server_fn):
        super(FakePowerControl, self).__init__(path)
        self.folder = path
        self.start_server_fn = start_server_fn
        self.stop_server_fn = stop_server_fn

        self._lock = threading.Lock()
        self.pdu_sims = {}
        self.sim_servers = {}

        if self.folder:
            self._load_pdu_sims()

    def setup(self, psu_count):
        outlets = {}
        for n in range(0, psu_count):
            name = "pdu%.3d" % n
            port = BASE_PDU_SERVER_PORT + n
            # FIXME: Make the type of PDU sim configurable
            pdu_sim = APC79xxSimulator(self.folder, PDU_SERVER_ADDRESS, port, name, outlets, self.server_poweroff_hook, self.server_poweron_hook)
            self.pdu_sims[name] = pdu_sim

    @property
    def next_outlet_index(self):
        from itertools import groupby
        from operator import itemgetter

        # Outlet index always starts at 1, to match PDU convention
        if len(self.state['server_outlets']) == 0:
            return 1

        outlets = sorted([int(o) for o in self.state['server_outlets'].values()])
        outlets.insert(0, 0)
        groups = [map(itemgetter(1), g) for _, g in groupby(enumerate(outlets), lambda (i, x): i - x)]

        # If we have a contiguous series of outlets, just append to it
        if len(groups) == 1:
            return outlets[-1] + 1

        # Otherwise, append after the first gap
        return groups[0][-1] + 1

    def add_server(self, fqdn):
        assert fqdn not in self.state['server_outlets']
        with self._lock:
            outlet = str(self.next_outlet_index)
            for pdu in self.pdu_sims.values():
                pdu.add_outlet(outlet)
            self.state['server_outlets'][fqdn] = outlet
            self.state['outlet_servers'][outlet] = fqdn
            self.save()

    def remove_server(self, fqdn):
        with self._lock:
            try:
                outlet = self.state['server_outlets'][fqdn]
                del(self.state['server_outlets'][fqdn])
                del(self.state['outlet_servers'][outlet])
                self.save()
            except KeyError:
                pass

    def server_outlet_number(self, fqdn):
        return self.state['server_outlets'][fqdn]

    def outlet_server_name(self, outlet):
        return self.state['outlet_servers'][outlet]

    @property
    def server_outlet_list(self):
        return sorted(self.state['server_outlets'].values())

    def server_has_power(self, fqdn):
        """
        Checks to see if any of the server's virtual PSUs have power. If none
        of the associated PDU outlets are on, then the server is considered
        to be powered off. Note that a multi-PSU server will be considered to
        be powered on if any or all of its virtual PSUs have power.
        """
        with self._lock:
            outlet = self.state['server_outlets'][fqdn]
            return any([pdu.outlet_is_on(outlet) for pdu in self.pdu_sims.values()])

    def server_poweroff_hook(self, outlet):
        """
        When an outlet has been turned off, checks to see if the associated
        server has lost all powered outlets. If so, the server is stopped.
        """
        fqdn = self.state['outlet_servers'][outlet]

        if not self.server_has_power(fqdn):
            log.debug("stopping %s in poweroff_hook" % fqdn)
            self.stop_server_fn(fqdn)

    def server_poweron_hook(self, outlet):
        """
        When an outlet has been turned on, attempts to start the associated
        server. If the server has already been started, this is a no-op.
        """
        fqdn = self.state['outlet_servers'][outlet]

        log.debug("starting %s in poweron_hook" % fqdn)
        self.start_server_fn(fqdn)

    def start_sim_server(self, pdu_name):
        log.debug("starting server for %s" % pdu_name)
        assert pdu_name not in self.sim_servers
        pdu = self.pdu_sims[pdu_name]
        self.sim_servers[pdu_name] = PDUSimulatorServer(pdu)
        self.sim_servers[pdu_name].start()

    def start(self):
        log.info("Power control: starting...")
        for pdu_name in self.pdu_sims:
            self.start_sim_server(pdu_name)

    def stop(self):
        log.info("Power control: stopping...")
        for sim_server in self.sim_servers.values():
            sim_server.stop()

    def join(self):
        log.info("Power control: joining...")
        for sim_server in self.sim_servers.values():
            sim_server.join()
