# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import xml.etree.ElementTree as xml
from xml.parsers.expat import ExpatError as ParseError
import socket

from chroma_agent.lib.shell import AgentShell
from chroma_agent.lib import fence_agents
from iml_common.lib import util


class PacemakerError(Exception):
    pass


class PacemakerConfigurationError(PacemakerError):
    def __str__(self):
        hostname = socket.gethostname()
        return "Pacemaker is either unconfigured or not started on %s" % hostname


class PacemakerObject(object):
    def __init__(self, element=None):
        if element:
            self.element = element

    def __getattr__(self, attr):
        for source in [self.__dict__, self.element.attrib]:
            try:
                return source[attr]
            except KeyError, AttributeError:
                pass

        raise AttributeError("'%s' has no attribute '%s'" % (self.__class__.__name__, attr))


class LustreTarget(PacemakerObject):
    @property
    def uuid(self):
        for nvpair in self.element.findall('./instance_attributes/nvpair'):
            if nvpair.get('name') == "target":
                return nvpair.get('value')


# TODO: Refactor this class to use PacemakerObject
class PacemakerNode(object):
    def __init__(self, name, uuid):
        self.name = name
        self.uuid = uuid
        self.attributes = {}

    def fence_reboot(self):
        self.fence_off()
        self.fence_on()

    def fence_off(self):
        if self.attributes.get('standby', "off") != "on":
            for agent in self.fence_agents:
                agent.off()

    def fence_on(self):
        if self.attributes.get('standby', "off") != "on":
            for agent in self.fence_agents:
                agent.on()

    @property
    def fence_agents(self):
        agents = []
        for kwargs in self.fence_agent_kwargs:
            try:
                agents.append(getattr(fence_agents, kwargs['agent'])(**kwargs))
            except AttributeError:
                raise PacemakerError("No FenceAgent class for %s" % kwargs['agent'])
        return agents

    @property
    def fence_agent_kwargs(self):
        kwargs = []
        for ad in self.fence_agent_dicts:
            new = {}
            for k, v in ad.items():
                new[k[k.rfind('fence_') + 6:]] = v
            kwargs.append(new)
        return kwargs

    @property
    def fence_agent_dicts(self):
        agents = []
        for agent in [k for k in self.attributes if 'agent' in k]:
            index = agent[0:agent.find('_')]
            agents.append(dict([t for t in self.attributes.items()
                                if t[0].startswith("%s_fence_" % index)]))

        return agents

    def set_fence_attributes(self, index, attributes):
        # HYD-2014: Make sure we set the N_fence_agent attribute last
        # in order to avoid races.
        agent = attributes.pop('agent')
        for key, value in attributes.items():
            self.set_attribute("%s_fence_%s" % (index, key), value)
        self.set_attribute("%s_fence_agent" % index, agent)

    def clear_fence_attributes(self):
        # HYD-2014: Make sure we remove the N_fence_agent attribute first
        # in order to avoid races.
        for fence_agent in self.fence_agent_dicts:
            key = [a for a in fence_agent if 'fence_agent' in a][0]
            del fence_agent[key]
            self.clear_attribute(key)

            for agent_attr in fence_agent:
                self.clear_attribute(agent_attr)

    def enable_standby(self):
        AgentShell.try_run(["crm_attribute", "-N", self.name, "-n", "standby", "-v", "on", "--lifetime=forever"])

    def disable_standby(self):
        AgentShell.try_run(["crm_attribute", "-N", self.name, "-n", "standby", "-v", "off", "--lifetime=forever"])

    # These crm_attribute options are undocumented, but they're exactly
    # what the crm utility uses when it does its thing. The documented
    # options don't actually work! Fun.
    def set_attribute(self, key, value):
        AgentShell.try_run(["crm_attribute", "-t", "nodes", "-U", self.name, "-n", key, "-v", str(value)])

    def clear_attribute(self, key):
        AgentShell.try_run(["crm_attribute", "-D", "-t", "nodes", "-U", self.name, "-n", key])


class PacemakerConfig(object):
    def __init__(self):
        if not self.cib_available:
            raise PacemakerConfigurationError()

    @property
    def cib_available(self):
        try:
            # Use --local because we're just testing to see if the cib
            # daemon is running at all.
            cibadmin(["--query", "--local"], timeout=10)
            return True
        except AgentShell.CommandExecutionError as e:
            # Known exception caused by the service being unconfigured or
            # not started.
            if e.rc == 107:
                return False
            else:
                raise e

    @property
    def root(self):
        result = cibadmin(["--query"])
        try:
            return xml.fromstring(result.stdout)
        except ParseError:
            raise PacemakerConfigurationError()

    @property
    def configuration(self):
        return self.root.find('configuration')

    @property
    def crm_config(self):
        return self.configuration.find('crm_config')

    @property
    def nodes(self):
        nodes = []
        for node in self.configuration.find('nodes'):
            nodeobj = PacemakerNode(node.get('uname'), node.get('id'))
            try:
                i_attrs = node.find('instance_attributes')
                for nvpair in i_attrs.findall('nvpair'):
                    nodeobj.attributes[nvpair.get('name')] = nvpair.get('value')
            except AttributeError:
                # No instance_attributes
                pass
            nodes.append(nodeobj)

        return nodes

    @property
    def lustre_targets(self):
        targets = []
        for primitive in self.configuration.findall("./resources/primitive"):
            if primitive.attrib['type'] == "Target":
                targets.append(LustreTarget(primitive))

        return targets

    @property
    def dc(self):
        dc_uuid = self.root.get('dc-uuid')

        if dc_uuid:
            try:
                return next(node.name for node in self.nodes if node.uuid == dc_uuid)
            except StopIteration:
                pass

        return None

    @property
    def fenceable_nodes(self):
        return [n for n in self.nodes if len(n.fence_agents) > 0]

    def get_node(self, node_name):
        try:
            return next(n for n in self.nodes if socket.getfqdn(n.name) == socket.getfqdn(node_name))
        except IndexError:
            raise PacemakerError("%s does not exist in pacemaker" % node_name)

    @property
    def is_dc(self):
        return self.dc == self.get_node(socket.gethostname()).name

    @property
    def configured(self):
        ''' configured returns True if this node has a pacemaker configuration set by IML.
        :return: True if configuration present else False
        '''
        return 'fence_chroma' in AgentShell.try_run(['cibadmin', '--query', '-o', 'resource'])

    def get_property_setvalue(self, property_set_name, value_name):
        '''
        :return: Value 'value_name' from a property set of name 'property_set_name'. None if no value.
        '''
        property_set = self.get_propertyset(property_set_name)

        return property_set.get(value_name, None)

    def create_update_properyset(self, propertyset_name, properties):
        nvpairs = ""

        for key, value in properties.items():
            nvpairs += '<nvpair id="%s-%s" name="%s" value="%s"/>\n' % (propertyset_name, key, key, value)

        cibadmin(["--modify", "--allow-create", "-o", "crm_config", "-X",
                  '<cluster_property_set id="%s">\n%s' % (propertyset_name, nvpairs)])

    def get_propertyset(self, propertyset_name):
        result = {}

        for propertyset in self.crm_config:
            if propertyset.attrib['id'] == propertyset_name:
                for value_pair in propertyset:
                    result[value_pair.attrib['name']] = value_pair.attrib['value']

        return result


def cibadmin(command_args, timeout=120):
    assert timeout > 0, 'timeout must be greater than zero'

    # I think these are "errno" values, but I'm not positive
    # but going forward, any additions to this should try to be informative
    # about the type of exit code and why it's OK to retry
    RETRY_CODES = {
        10: "something unknown",
        41: "something unknown",
        62: "Timer expired",
        107: "Transport endpoint is not connected"
    }

    command_args.insert(0, 'cibadmin')
    # NB: This isn't a "true" timeout, in that it won't forcibly stop the
    # subprocess after a timeout. We'd need more invasive changes to
    # shell._run() for that.
    for _ in util.wait(timeout):
        result = AgentShell.run(command_args)

        if result.rc == 0:
            return result
        elif result.rc not in RETRY_CODES:
            break

    # Add some harmless diagnostics which will be visible in the logs.
    AgentShell.run(['service', 'corosync', 'status'])
    AgentShell.run(['service', 'pacemaker', 'status'])

    if result.rc in RETRY_CODES:
        raise PacemakerError("%s timed out after %d seconds: rc: %s, stderr: %s"
                             % (" ".join(command_args), timeout, result.rc, result.stderr))
    else:
        raise AgentShell.CommandExecutionError(result, command_args)


def pacemaker_running():
    result = AgentShell.run(['service', 'pacemaker', 'status'])

    return result.rc == 0
