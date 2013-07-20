#
# INTEL CONFIDENTIAL
#
# Copyright 2013 Intel Corporation All Rights Reserved.
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


import xml.etree.ElementTree as xml
from xml.parsers.expat import ExpatError as ParseError

from chroma_agent import shell
from chroma_agent.lib import fence_agents
from time import sleep
import socket


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
    def __init__(self, name, attributes=None):
        self.name = name
        self.attributes = attributes
        if not self.attributes:
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
                raise RuntimeError("No FenceAgent class for %s" % kwargs['agent'])
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
        shell.try_run(["crm_attribute", "-N", self.name, "-n", "standby", "-v", "on", "--lifetime=forever"])

    def disable_standby(self):
        shell.try_run(["crm_attribute", "-N", self.name, "-n", "standby", "-v", "off", "--lifetime=forever"])

    # These crm_attribute options are undocumented, but they're exactly
    # what the crm utility uses when it does its thing. The documented
    # options don't actually work! Fun.
    def set_attribute(self, key, value):
        shell.try_run(["crm_attribute", "-t", "nodes", "-U", self.name, "-n", key, "-v", str(value)])

    def clear_attribute(self, key):
        shell.try_run(["crm_attribute", "-D", "-t", "nodes", "-U", self.name, "-n", key])


class PacemakerConfig(object):
    @property
    def root(self):
        rc, raw, stderr = cibadmin(["--query"])
        try:
            return xml.fromstring(raw)
        except ParseError:
            raise RuntimeError("Unable to dump pacemaker config: is it running?")

    @property
    def configuration(self):
        return self.root.find('configuration')

    @property
    def nodes(self):
        nodes = []
        for node in self.configuration.find('nodes'):
            nodeobj = PacemakerNode(node.get('uname'))
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
        return self.root.get('dc-uuid')

    @property
    def fenceable_nodes(self):
        return [n for n in self.nodes if len(n.fence_agents) > 0]

    def get_node(self, node_name):
        try:
            return [n for n in self.nodes if n.name == node_name][0]
        except IndexError:
            raise RuntimeError("%s does not exist in pacemaker" % node_name)

    @property
    def is_dc(self):
        return self.dc == self.get_node(socket.gethostname()).name


def cibadmin(command_args):
    from chroma_agent import shell

    # try at most, 100 times
    n = 100
    rc = 10

    while (rc == 10 or rc == 41) and n > 0:
        rc, stdout, stderr = shell.run(['cibadmin'] + command_args)
        if rc == 0:
            break
        sleep(1)
        n -= 1

    if rc != 0:
        raise RuntimeError("Error (%s) running 'cibadmin %s': '%s' '%s'" %
                           (rc, " ".join(command_args), stdout, stderr))

    return rc, stdout, stderr
