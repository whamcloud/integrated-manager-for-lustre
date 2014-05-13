#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2014 Intel Corporation All Rights Reserved.
#
# The source code contained or described herein and all documents related
# to the source code ("Material") are owned by Intel Corporation or its
# suppliers or licensors. Title to the Material remains with Intel Corporation
# or its suppliers and licensors. The Material contains trade secrets and
# proprietary and confidential information of Intel or its suppliers and
# licensors. The Material is protected by worldwide copyright and trade secret
# laws and treaty provisions. No part of the Material may be used, copied,
# reproduced, modified, published, uploaded, posted, transmitted, distributed,
# or disclosed in any way without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be
# express and approved by Intel in writing.


import re
import os

from collections import defaultdict
from chroma_agent.log import daemon_log
from chroma_agent.plugin_manager import DevicePlugin
from chroma_agent import shell

EXCLUDE_INTERFACES = ['lo']


class NetworkInterface():
    ''' Created with an array of lines that are the output from ifconfig, this class will
    parse those lines and end up with a set of properties corresponding to the parsed data

    It only produces what is there and so some values may be left unset. The idea is that
    once parsed the results can be accessed using named properties.
    '''
    def __init__(self, ifconfig_lines):
        match_values = ['(?P<interface>^[a-zA-Z0-9:]+)(.*)Link encap:(.*).*',
                        '(.*)Link encap:(?P<type>[^\s]*).*(HWaddr )(?P<mac_address>[^\s]*).*',
                        '.*(inet addr:)(?P<inet4_addr>[^\s]*).*',
                        '.*(inet6 addr: )(?P<inet6_addr>[^\s\/]*/(?P<prefixlen>[\d]*)).*',
                        '.*(P-t-P:)(?P<ptp>[^\s]*).*',
                        '.*(Bcast:)(?P<inet4_broadcast>[^\s]*).*',
                        '.*(Mask:)(?P<inet4_mask>[^\s]*).*',
                        '\s*(?P<up>[a-zA-Z]+) BROADCAST.*',
                        '.*RUNNING (?P<slave>[a-zA-Z]+) MULTICAST.*',
                        '.*(Scope:)(?P<scopeid>[^\s]*).*',
                        '.*(RX bytes:)(?P<rx_bytes>\d+).*',
                        '.*(TX bytes:)(?P<tx_bytes>\d+).*']

        self._values = defaultdict(lambda: '')

        # Set some defaults
        self._values['up'] = 'DOWN'

        for line in ifconfig_lines:
            for match_value in match_values:
                m = re.match(match_value, line)
                if m:
                    self._values.update(m.groupdict())

    @property
    def interface(self):
        '''
        :return: str: The name of the device, for example eth0 or ib2, or '' if not present.
        '''
        return self._values["interface"]

    @property
    def mac_address(self):
        '''
        :return: str: Containing the mac address of the device, or '' if not present.
        '''
        return self._values["mac_address"]

    @property
    def type(self):
        '''
        :return: str: Containing the type of the interface, ethernet for example, or '' if not present.
        '''
        return self._values["type"]

    @property
    def inet4_addr(self):
        '''
        :return: str: Containing the type of the inet4 address of interface, or '' if not present.
        '''
        return self._values["inet4_addr"]

    @property
    def inet6_addr(self):
        '''
        :return: str: Containing the type of the inet6 address of interface, or '' if not present.
        '''
        return self._values["inet6_addr"]

    @property
    def rx_bytes(self):
        '''
        :return: str: Containing the type of the number of received bytes for the interface, or '' if not present.
        '''
        return self._values["rx_bytes"]

    @property
    def tx_bytes(self):
        '''
        :return: str: Containing the type of the number of transmitted bytes for the interface, or '' if not present.
        '''
        return self._values["tx_bytes"]

    @property
    def up(self):
        '''
        :return: bool: True if the device described as being by ifconfig as being in the up state
        '''
        return self._values["up"].upper() == 'UP'

    @property
    def slave(self):
        '''
        :return: bool: True if the device described by ifconfig as a slave device
        '''
        return self._values["slave"].upper() == 'SLAVE'


class NetworkInterfaces(dict):
    network_translation = {'ethernet': 'tcp',
                           'infiniband': 'o2ib'}

    class InterfaceNotFound(LookupError):
        pass

    def __init__(self):
        '''
        :return: A dist of dicts that describe all of the network interfaces on the node with
        the exception of the the lo interface which is excluded from the list.
        '''
        def interface_to_lnet_type(if_type):
            '''
            To keep everything consistant we report networks types as the lnd name not the linux name we
            have to translate somewhere so do it at source, if the user ever needs to see it as Linux types
            we can translate back.
            There is a train of thought that says it if is unknown we should cause an exception which means
            the app will not work, I prefer to try an approach that says returning just the unknown might
            well work, and if not it causes an exception somewhere else.
            '''
            return self.network_translation.get(if_type.lower(), if_type.lower())

        try:
            out = shell.try_run(['ifconfig', '-a'])
        except IOError:
            daemon_log.warning("ifconfig: failed to run")
            return []

        lines = out.split("\n")

        lines.append("")                # This empty line on the end just causes interfaces to get flushed in the loop below

        device_lines = []

        for line in lines:

            if (line == "") and (len(device_lines) > 0):             # Blank line end of device
                interface = NetworkInterface(device_lines)

                if (interface.interface not in EXCLUDE_INTERFACES) and (interface.slave == False):
                    self[interface.interface] = {'mac_address': interface.mac_address,
                                                 'inet4_address': interface.inet4_addr,
                                                 'inet6_address': interface.inet6_addr,
                                                 'type': interface_to_lnet_type(interface.type),
                                                 'rx_bytes': interface.rx_bytes,
                                                 'tx_bytes': interface.tx_bytes,
                                                 'up': interface.up,
                                                 'slave': interface.slave}

                device_lines = []

            if (line != ""):
                device_lines.append(line)

    def name(self, inet4_address):
        result = None

        if inet4_address == '0':
            result = 'lo'
        else:
            for name, interface in self.iteritems():
                if (interface['inet4_address'] == inet4_address):
                    result = name
                    break

        if result == None:
            raise self.InterfaceNotFound("Unable to find a name for the network address %s" % inet4_address)

        return result


class LNetNid():
    ''' Created with a single line that is the output of /proc/sys/lnet/nis, this class will
    parse those lines and end up with a set of properties corresponding to the parsed data

    It also requires a list of the network interfaces on the node so that it can name the nids
    with the interface name (eth0) for example. This name is required as it is more stable than
    the network address.
    '''
    def __init__(self, lnet_nis_line, interfaces):
        tokens = lnet_nis_line.split()

        assert(len(tokens) == 9)

        self.nid_address = tokens[0].split("@")[0]  # TODO: Need to convert to an interface
        type_network_no = tokens[0].split("@")[1]

        m = re.match('(\w+?)(\d+)?$', type_network_no)   # Non word, then optional greedy number at end of line.
        self.lnd_type = m.group(1)
        self.lnd_network = m.group(2)
        if not self.lnd_network:
            self.lnd_network = 0

        self.status = tokens[1]
        self.alive = tokens[2]
        self.refs = tokens[3]
        self.peer = tokens[4]
        self.rtr = tokens[5]
        self.max = tokens[6]
        self.tx = tokens[7]
        self.min = tokens[8]

        # I don't like this but we need to key on the name of the port the nid is associated with and
        # I can't see a better way than this to do it, feels clumsy.
        # Nasty, interfaces will not have an entry for lo which is at address '0' in lnet land so just fix
        # that exception up.
        # By default make the name the address, we need something in-case there is no match, and this makes it debuggable.
        self.name = interfaces.name(self.nid_address)


class LinuxNetworkDevicePlugin(DevicePlugin):
    # This need to be instance variables, for reasons that are really difficult to expliain.
    # Generally changes are sent but sometimes we want to poll them. However when we poll we create a new object
    # and so if these are instance variables we don't get the diff back, and so don't see the deletes!
    # last_return is updated in the session_update so a poll sees any deletes but does not stop them being sent in
    # the updates. Ask Chris about this for more info.
    last_return = {}
    cached_results = {}

    def __init__(self, session):
        super(LinuxNetworkDevicePlugin, self).__init__(session)

    def _lnet_devices(self, interfaces):
        '''
        :param interfaces: A list of the interfaces on the current node
        :return: Returns a dict of dicts describing the nids on the current node.
        '''
        # Read active NIDs from /proc
        try:
            lines = open("/proc/sys/lnet/nis").readlines()
        except IOError:
            daemon_log.warning("get_nids: failed to open")
            return LinuxNetworkDevicePlugin.cached_results

        # Skip header line
        lines = lines[1:]

        # Parse each NID string out into result list
        lnet_nids = []
        for line in lines:
            try:
                lnet_nids.append(LNetNid(line, interfaces))
            except NetworkInterfaces.InterfaceNotFound as e:
                daemon_log.warning(e)

        result = {}

        for lnet_nid in lnet_nids:
            if lnet_nid.lnd_type not in EXCLUDE_INTERFACES:
                result[lnet_nid.name] = {'nid_address': lnet_nid.nid_address,
                                         'lnd_type': lnet_nid.lnd_type,
                                         'lnd_network': lnet_nid.lnd_network}

            LinuxNetworkDevicePlugin.cache_results(raw_result = result)

        return result

    @classmethod
    def cache_results(cls, raw_result = None, lnet_configuration = None):
        assert (raw_result == None) or (lnet_configuration == None)

        if lnet_configuration:
            raw_result = {}

            interfaces = NetworkInterfaces()

            for network_interface in lnet_configuration['network_interfaces']:
                raw_result[interfaces.name(network_interface[0])] = {'nid_address': network_interface[0],
                                                                     'lnd_type': network_interface[1],
                                                                     'lnd_network': network_interface[2]}

        cls.cached_results = raw_result

    def _lnet_state(self):
        '''
        Uses /proc/module and /proc/sys/lnet/stats to decide is lnet is up, down or unloaded
        :return: lnet_up, lnet_down or lnet_unloaded
        '''
        lnet_loaded = False
        for module_line in open("/proc/modules").readlines():
            if module_line.startswith("lnet "):
                lnet_loaded = True
                break

        lnet_up = os.path.exists("/proc/sys/lnet/stats")

        return {(False, False): "lnet_unloaded",
                 (False, True): "lnet_unloaded",
                 (True, False): "lnet_down",
                 (True, True): "lnet_up"}[(lnet_loaded, lnet_up)]

    def start_session(self):
        interfaces = NetworkInterfaces()
        nids = self._lnet_devices(interfaces)

        result = {'interfaces': {'active': interfaces},
                  'lnet': {'state': self._lnet_state(),
                           'nids': {'active': nids}}}

        # Default to nothing deleted
        result['interfaces']['deleted'] = []
        result['lnet']['nids']['deleted'] = []

        if (LinuxNetworkDevicePlugin.last_return != {}):
            result['interfaces']['deleted'] = [item for item in LinuxNetworkDevicePlugin.last_return['interfaces']['active'] if item not in result['interfaces']['active']]
            result['lnet']['nids']['deleted'] = [item for item in LinuxNetworkDevicePlugin.last_return['lnet']['nids']['active'] if item not in result['lnet']['nids']['active']]

        return result

    def update_session(self):
        this_return = self.start_session()

        # THIS DOESN"T WORK BECAUSE RX/TX change in the network and so the data is sent back everytime. So it does work
        # but the data is always sent to if (true) is really what we have.
        if (this_return != self.last_return):
            LinuxNetworkDevicePlugin.last_return = this_return
            return self.last_return
        else:
            return
